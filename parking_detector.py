import cv2
import pickle
import numpy as np
import time
import os

class ParkingDetector:
    def __init__(self, pos_file='CarParkPos', video_source='carPark.mp4', width=107, height=48):
        self.pos_file = pos_file
        self.video_source = video_source
        self.width = width
        self.height = height
        self.pixel_threshold = 900
        self.blur_kernel = 3
        self.block_size = 25
        self.c_val = 16
        self.pos_list = []
        self.load_positions()
        
        # Latest telemetry state
        self.latest_stats = {
            "total_slots": len(self.pos_list),
            "occupied_slots": 0,
            "available_slots": len(self.pos_list),
            "occupancy_rate": 0.0,
            "slots": [],
            "timestamp": time.time()
        }

    def load_positions(self):
        """Loads parking slot coordinates from pickle file."""
        if os.path.exists(self.pos_file):
            try:
                with open(self.pos_file, 'rb') as f:
                    self.pos_list = pickle.load(f)
            except Exception as e:
                print(f"Error loading {self.pos_file}: {e}")
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

    def process_frame(self, img):
        """
        Processes a raw BGR image frame and calculates parking slot statuses.
        Returns (annotated_image, stats_dict).
        """
        if img is None:
            return None, self.latest_stats

        # Image processing pipeline
        img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Kernel size must be odd and >= 1
        k_size = max(1, self.blur_kernel if self.blur_kernel % 2 == 1 else self.blur_kernel + 1)
        img_blur = cv2.GaussianBlur(img_gray, (k_size, k_size), 1)
        
        # Block size must be odd and > 1
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

        annotated_img = img.copy()

        for idx, pos in enumerate(self.pos_list):
            x, y = pos
            img_crop = img_dilate[y:y + self.height, x:x + self.width]
            count = cv2.countNonZero(img_crop)
            is_available = count < self.pixel_threshold

            if is_available:
                color = (0, 230, 118)  # Glowing Green (BGR)
                thickness = 3
                available_count += 1
            else:
                color = (48, 48, 255)  # Vibrant Red (BGR)
                thickness = 2
                occupied_count += 1

            # Draw parking rectangle
            cv2.rectangle(annotated_img, pos, (x + self.width, y + self.height), color, thickness)
            
            # Draw slot label inside
            label_text = f"P{idx + 1}"
            cv2.putText(
                annotated_img, label_text, (x + 6, y + 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA
            )

            slots_data.append({
                "id": idx + 1,
                "x": x,
                "y": y,
                "occupied": not is_available,
                "pixel_count": count
            })

        total = len(self.pos_list)
        occupancy_rate = round((occupied_count / total * 100), 1) if total > 0 else 0.0

        # Draw overall status overlay banner on top-left of image
        banner_text = f"AVAILABLE: {available_count}/{total}"
        cv2.rectangle(annotated_img, (20, 20), (320, 70), (15, 23, 42), -1)
        cv2.rectangle(annotated_img, (20, 20), (320, 70), (56, 189, 248), 2)
        cv2.putText(
            annotated_img, banner_text, (35, 53),
            cv2.FONT_HERSHEY_SIMPLEX, 0.85, (0, 230, 118), 2, cv2.LINE_AA
        )

        self.latest_stats = {
            "total_slots": total,
            "occupied_slots": occupied_count,
            "available_slots": available_count,
            "occupancy_rate": occupancy_rate,
            "slots": slots_data,
            "timestamp": time.time()
        }

        return annotated_img, self.latest_stats

    def generate_frames(self):
        """
        MJPEG stream generator that reads frames from video_source in a continuous loop.
        """
        cap = cv2.VideoCapture(self.video_source)
        if not cap.isOpened():
            print(f"Error opening video source: {self.video_source}")
            return

        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        frame_delay = 1.0 / fps

        while True:
            # Loop video when reaching end
            if cap.get(cv2.CAP_PROP_POS_FRAMES) == cap.get(cv2.CAP_PROP_FRAME_COUNT):
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

            success, frame = cap.read()
            if not success:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue

            annotated_frame, _ = self.process_frame(frame)

            # Encode as JPEG
            ret, buffer = cv2.imencode('.jpg', annotated_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
            if not ret:
                continue

            frame_bytes = buffer.tobytes()

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

            time.sleep(frame_delay)
