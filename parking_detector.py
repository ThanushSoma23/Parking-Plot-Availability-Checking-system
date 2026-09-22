import cv2
import pickle
import numpy as np
import time
import os
import json
import logging
import threading
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AI1_ParkingDetector")

class ParkingAreaDetector:
    """
    OpenCV-based physical occupancy detector for a single parking area.
    Operates an isolated background thread to read video frames and compute
    slot-level physical occupancy (AVAILABLE or OCCUPIED).
    """
    def __init__(
        self,
        area_id,
        name,
        pos_file,
        video_source,
        pixel_threshold=900,
        video_loop=True,
        width=107,
        height=48,
        blur_kernel=3,
        block_size=25,
        c_val=16,
        playback_speed=1.5
    ):
        self.area_id = int(area_id)
        self.name = str(name)
        self.pos_file = str(pos_file)
        self.video_source = str(video_source)
        self.pixel_threshold = int(pixel_threshold)
        self.video_loop = bool(video_loop)
        self.width = int(width)
        self.height = int(height)
        self.blur_kernel = int(blur_kernel)
        self.block_size = int(block_size)
        self.c_val = int(c_val)
        self.playback_speed = float(playback_speed)

        self.pos_list = []
        self.reserved_slots = set()
        self.lock = threading.Lock()
        self.current_annotated_frame = None

        self.is_healthy = False
        self.health_error = None

        # Perform explicit startup verification
        self._perform_startup_check()

        # Initialize physical & legacy stats data structure
        total_len = len(self.pos_list)
        self.latest_stats = {
            "total_slots": total_len,
            "occupied_slots": 0,
            "available_slots": total_len,
            "occupancy_rate": 0.0,
            "slots": [],
            "timestamp": time.time()
        }

        self.latest_physical_stats = {
            "parkingAreaId": self.area_id,
            "name": self.name,
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "source": os.path.basename(self.video_source),
            "totalSlots": total_len,
            "availableSlots": total_len,
            "occupiedSlots": 0,
            "occupancyPercentage": 0.0,
            "slots": [
                {
                    "slotId": idx + 1,
                    "slotNumber": f"A{idx+1:02d}",
                    "status": "AVAILABLE"
                } for idx in range(total_len)
            ]
        }

        # Start isolated background video thread if healthy
        self.running = True
        self.thread = threading.Thread(target=self._update_loop, daemon=True)
        self.thread.start()

    def _perform_startup_check(self):
        """
        Explicitly checks if position file and video source exist and are readable at startup.
        Logs failure immediately if files are missing or corrupt.
        """
        # 1. Position File Check
        if not os.path.exists(self.pos_file):
            self.is_healthy = False
            self.health_error = f"Position file '{self.pos_file}' missing for area {self.area_id}."
            logger.error(f"[Area {self.area_id} - '{self.name}'] STARTUP ERROR: {self.health_error}")
            return

        try:
            with open(self.pos_file, 'rb') as f:
                self.pos_list = pickle.load(f)
            if not isinstance(self.pos_list, list):
                raise ValueError("Position data must be a list of coordinates.")
        except Exception as e:
            self.is_healthy = False
            self.health_error = f"Failed to load position file '{self.pos_file}': {e}"
            logger.error(f"[Area {self.area_id} - '{self.name}'] STARTUP ERROR: {self.health_error}")
            return

        # 2. Video Source Check
        if not os.path.exists(self.video_source):
            self.is_healthy = False
            self.health_error = f"Video source '{self.video_source}' missing for area {self.area_id}."
            logger.error(f"[Area {self.area_id} - '{self.name}'] STARTUP ERROR: {self.health_error}")
            return

        cap = cv2.VideoCapture(self.video_source)
        if not cap.isOpened():
            cap.release()
            self.is_healthy = False
            self.health_error = f"Could not open video file '{self.video_source}' for area {self.area_id}."
            logger.error(f"[Area {self.area_id} - '{self.name}'] STARTUP ERROR: {self.health_error}")
            return

        ret, frame = cap.read()
        cap.release()

        if not ret or frame is None:
            self.is_healthy = False
            self.health_error = f"Failed to read initial frame from '{self.video_source}' for area {self.area_id}."
            logger.error(f"[Area {self.area_id} - '{self.name}'] STARTUP ERROR: {self.health_error}")
            return

        self.is_healthy = True
        self.health_error = None
        logger.info(f"[Area {self.area_id} - '{self.name}'] STARTUP SUCCESS: Initialized with {len(self.pos_list)} slots from '{self.pos_file}' and video '{self.video_source}'.")

    def load_positions(self):
        """Reloads parking slot coordinates from pickle file."""
        if os.path.exists(self.pos_file):
            try:
                with open(self.pos_file, 'rb') as f:
                    self.pos_list = pickle.load(f)
            except Exception as e:
                logger.error(f"Error loading {self.pos_file}: {e}")
                self.pos_list = []
        else:
            self.pos_list = []
        return self.pos_list

    def save_positions(self, new_pos_list=None):
        """Saves parking slot coordinates to pickle file."""
        if new_pos_list is not None:
            self.pos_list = new_pos_list
        with open(self.pos_file, 'wb') as f:
            pickle.dump(self.pos_list, f)

    def reserve_slot(self, slot_id):
        """Reserves a specific slot by its ID (legacy endpoint support)."""
        with self.lock:
            self.reserved_slots.add(int(slot_id))

    def release_slot(self, slot_id):
        """Releases a reservation for a specific slot."""
        with self.lock:
            self.reserved_slots.discard(int(slot_id))

    def process_frame(self, img):
        """
        Processes a raw BGR image frame and calculates parking slot occupancy.
        Returns (annotated_image, stats_dict).
        """
        if img is None:
            return None, self.latest_stats

        # Image processing pipeline
        img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        k_size = max(1, self.blur_kernel if self.blur_kernel % 2 == 1 else self.blur_kernel + 1)
        img_blur = cv2.GaussianBlur(img_gray, (k_size, k_size), 1)
        
        b_size = max(3, self.block_size if self.block_size % 2 == 1 else self.block_size + 1)
        img_thresh = cv2.adaptiveThreshold(
            img_blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV, b_size, self.c_val
        )
        img_median = cv2.medianBlur(img_thresh, 5)
        kernel = np.ones((3, 3), np.uint8)
        img_dilate = cv2.dilate(img_median, kernel, iterations=1)

        available_count = 0
        occupied_count = 0
        slots_data = []

        phys_available_count = 0
        phys_occupied_count = 0
        phys_slots_data = []

        annotated_img = img.copy()

        for idx, pos in enumerate(self.pos_list):
            x, y = pos
            slot_id = idx + 1
            slot_number = f"A{slot_id:02d}"

            y1, y2 = max(0, y), min(img_dilate.shape[0], y + self.height)
            x1, x2 = max(0, x), min(img_dilate.shape[1], x + self.width)
            img_crop = img_dilate[y1:y2, x1:x2]

            count = cv2.countNonZero(img_crop) if img_crop.size > 0 else 0
            is_reserved = slot_id in self.reserved_slots
            is_camera_occupied = count >= self.pixel_threshold

            # Pure physical status for AI-1 API
            if is_camera_occupied:
                phys_status = "OCCUPIED"
                phys_occupied_count += 1
            else:
                phys_status = "AVAILABLE"
                phys_available_count += 1

            phys_slots_data.append({
                "slotId": slot_id,
                "slotNumber": slot_number,
                "status": phys_status
            })

            # Legacy status calculation for UI overlay & legacy endpoints
            if is_reserved:
                status = "RESERVED"
                color = (29, 107, 154)  # BGR Reserved
                thickness = 2
                occupied_count += 1
            elif is_camera_occupied:
                status = "OCCUPIED"
                color = (80, 83, 239)   # BGR Occupied
                thickness = 2
                occupied_count += 1
            else:
                status = "AVAILABLE"
                color = (138, 134, 133) # BGR Available
                thickness = 3
                available_count += 1

            cv2.rectangle(annotated_img, (x, y), (x + self.width, y + self.height), color, thickness)
            cv2.putText(
                annotated_img, f"{slot_number}", (x + 6, y + 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (245, 245, 245), 1, cv2.LINE_AA
            )

            slots_data.append({
                "id": slot_id,
                "slotNumber": slot_number,
                "x": x,
                "y": y,
                "occupied": status != "AVAILABLE",
                "status": status,
                "pixel_count": count
            })

        total = len(self.pos_list)
        occupancy_rate = round((occupied_count / total * 100), 1) if total > 0 else 0.0
        phys_rate = round((phys_occupied_count / total * 100), 2) if total > 0 else 0.0
        iso_timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        # Top-left visual banner
        banner_text = f"AREA {self.area_id} AVAILABLE: {available_count}/{total}"
        cv2.rectangle(annotated_img, (20, 20), (350, 70), (41, 32, 29), -1)
        cv2.rectangle(annotated_img, (20, 20), (350, 70), (36, 170, 245), 2)
        cv2.putText(
            annotated_img, banner_text, (30, 53),
            cv2.FONT_HERSHEY_SIMPLEX, 0.75, (122, 196, 57), 2, cv2.LINE_AA
        )

        stats = {
            "total_slots": total,
            "occupied_slots": occupied_count,
            "available_slots": available_count,
            "occupancy_rate": occupancy_rate,
            "slots": slots_data,
            "timestamp": time.time()
        }

        physical_stats = {
            "parkingAreaId": self.area_id,
            "name": self.name,
            "timestamp": iso_timestamp,
            "source": os.path.basename(self.video_source),
            "totalSlots": total,
            "availableSlots": phys_available_count,
            "occupiedSlots": phys_occupied_count,
            "occupancyPercentage": phys_rate,
            "slots": phys_slots_data
        }

        with self.lock:
            self.latest_physical_stats = physical_stats

        return annotated_img, stats

    def _update_loop(self):
        """
        Isolated background thread loop for reading video frames and updating stats.
        Handles video looping based on video_loop flag.
        """
        if not self.is_healthy:
            logger.warning(f"[Area {self.area_id}] Thread idle due to startup error.")
            return

        cap = cv2.VideoCapture(self.video_source)

        while self.running:
            if not cap.isOpened():
                time.sleep(0.5)
                if self.video_loop and self.running:
                    cap = cv2.VideoCapture(self.video_source)
                else:
                    break
                continue

            speed = max(0.2, float(self.playback_speed))
            if speed > 1.2:
                skip_count = int(speed) - 1
                for _ in range(skip_count):
                    cap.grab()

            success, frame = cap.read()
            if not success or frame is None:
                cap.release()
                if self.video_loop and self.running:
                    cap = cv2.VideoCapture(self.video_source)
                    time.sleep(0.04)
                    continue
                else:
                    logger.info(f"[Area {self.area_id}] Video reached end (videoLoop=False).")
                    break

            annotated_frame, stats = self.process_frame(frame)

            with self.lock:
                self.current_annotated_frame = annotated_frame
                self.latest_stats = stats

            target_delay = max(0.005, (1.0 / (24.0 * speed)))
            time.sleep(target_delay)

        if cap.isOpened():
            cap.release()

    def stop(self):
        """Stops the background thread cleanly."""
        self.running = False

    def get_latest_frame(self):
        """Thread-safe retrieval of the latest processed frame."""
        with self.lock:
            if self.current_annotated_frame is not None:
                return self.current_annotated_frame.copy()
            return None

    def get_latest_stats(self):
        """Thread-safe retrieval of legacy statistics."""
        with self.lock:
            return self.latest_stats

    def get_latest_physical_stats(self):
        """Thread-safe retrieval of official AI-1 physical occupancy statistics."""
        with self.lock:
            if not self.latest_physical_stats:
                return None
            stats = dict(self.latest_physical_stats)
            stats["timestamp"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            stats["slots"] = [dict(s) for s in stats.get("slots", [])]
            return stats

    def generate_frames(self):
        """MJPEG stream generator yielding latest JPEG encoded frames."""
        while self.running:
            frame = self.get_latest_frame()
            if frame is None:
                time.sleep(0.04)
                continue

            ret, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
            if not ret:
                time.sleep(0.04)
                continue

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

            speed = max(0.2, float(self.playback_speed))
            target_delay = max(0.005, (1.0 / (24.0 * speed)))
            time.sleep(target_delay)


class ParkingDetectorManager:
    """
    Manager class for loading parking_areas.json and orchestrating multiple ParkingAreaDetector instances.
    """
    def __init__(self, config_file='parking_areas.json'):
        self.config_file = config_file
        self.detectors = {}
        self.area_configs = []
        self.load_config_and_init_detectors()

    def load_config_and_init_detectors(self):
        """Loads configuration and instantiates detectors at startup."""
        if not os.path.exists(self.config_file):
            logger.error(f"[AI-1 Manager] Configuration file '{self.config_file}' not found.")
            return

        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self.area_configs = json.load(f)
        except Exception as e:
            logger.error(f"[AI-1 Manager] Error loading '{self.config_file}': {e}")
            self.area_configs = []
            return

        logger.info(f"[AI-1 Manager] Initializing {len(self.area_configs)} configured parking areas...")

        for area_cfg in self.area_configs:
            area_id = int(area_cfg.get("parkingAreaId"))
            detector = ParkingAreaDetector(
                area_id=area_id,
                name=area_cfg.get("name", f"Area {area_id}"),
                pos_file=area_cfg.get("posFile", "CarParkPos"),
                video_source=area_cfg.get("videoSource", "carPark.mp4"),
                pixel_threshold=area_cfg.get("pixelThreshold", 900),
                video_loop=area_cfg.get("videoLoop", True)
            )
            self.detectors[area_id] = detector

    def get_detector(self, area_id):
        """Retrieves detector instance by parking area ID."""
        try:
            a_id = int(area_id)
            return self.detectors.get(a_id)
        except (ValueError, TypeError):
            return None

    def get_all_areas_info(self):
        """
        Returns dynamic discovery list of all configured parking areas.
        totalSlots is dynamically read from each area's loaded pos_list!
        """
        areas_list = []
        for area_id, detector in sorted(self.detectors.items()):
            areas_list.append({
                "id": detector.area_id,
                "name": detector.name,
                "totalSlots": len(detector.pos_list),
                "isHealthy": detector.is_healthy
            })
        return areas_list

    def stop_all(self):
        """Cleanly stops all background detector threads."""
        logger.info("[AI-1 Manager] Stopping all background detector threads...")
        for detector in self.detectors.values():
            detector.stop()
