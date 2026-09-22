import unittest
import os
import sys
import json
import pickle
from unittest.mock import patch

# Ensure project root is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from server import app, detector_manager
from parking_detector import ParkingAreaDetector

class TestMultiAreaAI1OccupancyAPI(unittest.TestCase):
    def setUp(self):
        app.testing = True
        self.client = app.test_client()

    def test_get_areas_discovery_endpoint(self):
        """Test GET /api/v1/areas returns all configured parking areas with dynamic totalSlots."""
        response = self.client.get('/api/v1/areas')
        self.assertEqual(response.status_code, 200)

        areas = json.loads(response.data)
        self.assertIsInstance(areas, list)
        self.assertGreaterEqual(len(areas), 3)

        # Verify dynamic slot count matching each area's CarParkPos file
        for area in areas:
            area_id = area["id"]
            self.assertIn("name", area)
            self.assertIn("totalSlots", area)
            self.assertIn("isHealthy", area)

            detector = detector_manager.get_detector(area_id)
            self.assertIsNotNone(detector, f"Detector for area {area_id} missing from manager.")

            # Dynamically verify slot count matches actual pos file
            if os.path.exists(detector.pos_file):
                with open(detector.pos_file, 'rb') as f:
                    pos_data = pickle.load(f)
                self.assertEqual(area["totalSlots"], len(pos_data))

    def test_get_occupancy_parametrized_across_all_areas(self):
        """Test GET /api/v1/occupancy/{id} for all configured area IDs (1, 2, 3)."""
        area_ids = [cfg["parkingAreaId"] for cfg in detector_manager.area_configs]

        for area_id in area_ids:
            detector = detector_manager.get_detector(area_id)
            self.assertIsNotNone(detector)

            response = self.client.get(f'/api/v1/occupancy/{area_id}')
            self.assertEqual(response.status_code, 200, f"Area {area_id} returned status {response.status_code}")

            data = json.loads(response.data)

            # 1. Top-level keys check
            self.assertEqual(data["parkingAreaId"], area_id)
            self.assertIn("name", data)
            self.assertIn("timestamp", data)
            self.assertIn("source", data)
            self.assertIn("totalSlots", data)
            self.assertIn("availableSlots", data)
            self.assertIn("occupiedSlots", data)
            self.assertIn("occupancyPercentage", data)
            self.assertIn("slots", data)

            # 2. Dynamic totalSlots check from posFile (no hardcoded literal numbers!)
            with open(detector.pos_file, 'rb') as f:
                pos_data = pickle.load(f)
            expected_total = len(pos_data)

            self.assertEqual(data["totalSlots"], expected_total)
            self.assertEqual(len(data["slots"]), expected_total)

            # 3. Aggregate consistency checks
            total = data["totalSlots"]
            available = data["availableSlots"]
            occupied = data["occupiedSlots"]

            self.assertEqual(total, available + occupied)

            if total > 0:
                expected_pct = round((occupied / total * 100), 2)
                self.assertAlmostEqual(data["occupancyPercentage"], expected_pct, places=2)

            # 4. Status constraint check (must be ONLY AVAILABLE or OCCUPIED)
            allowed_statuses = {"AVAILABLE", "OCCUPIED"}
            seen_ids = set()

            for slot in data["slots"]:
                s_id = slot["slotId"]
                s_status = slot["status"]

                self.assertNotIn(s_id, seen_ids, f"Duplicate slotId {s_id} in area {area_id}")
                seen_ids.add(s_id)

                self.assertIn(s_status, allowed_statuses)
                self.assertNotEqual(s_status, "RESERVED", "AI-1 must not return RESERVED status")

            if expected_total > 0:
                self.assertEqual(seen_ids, set(range(1, expected_total + 1)))

    def test_invalid_parking_area_id_returns_400(self):
        """Test 400 Bad Request for invalid IDs."""
        for invalid_id in ["0", "-1", "-10", "abc"]:
            response = self.client.get(f'/api/v1/occupancy/{invalid_id}')
            self.assertEqual(response.status_code, 400)
            data = json.loads(response.data)
            self.assertEqual(data.get("code"), "INVALID_PARKING_AREA_ID")

    def test_unconfigured_area_id_gap_returns_404(self):
        """Test 404 Not Found for unconfigured area ID gaps (e.g. 4, 99)."""
        for gap_id in [4, 99, 500]:
            response = self.client.get(f'/api/v1/occupancy/{gap_id}')
            self.assertEqual(response.status_code, 404)
            data = json.loads(response.data)
            self.assertEqual(data.get("code"), "PARKING_AREA_NOT_FOUND")

    def test_area_startup_failure_isolation(self):
        """
        Test area failure isolation: if one area fails startup checks (missing video/pos),
        that specific area returns HTTP 500 while other areas remain healthy and respond 200 OK.
        """
        # Create an unhealthy detector with missing files
        unhealthy_detector = ParkingAreaDetector(
            area_id=99,
            name="Corrupt Test Area",
            pos_file="non_existent_pos_file.pickle",
            video_source="non_existent_video.mp4"
        )
        unhealthy_detector.stop()

        self.assertFalse(unhealthy_detector.is_healthy)
        self.assertIsNotNone(unhealthy_detector.health_error)

        # Inject into manager registry temporarily
        with patch.dict(detector_manager.detectors, {99: unhealthy_detector}):
            # Unhealthy area 99 must return 500
            response_unhealthy = self.client.get('/api/v1/occupancy/99')
            self.assertEqual(response_unhealthy.status_code, 500)
            data_unhealthy = json.loads(response_unhealthy.data)
            self.assertEqual(data_unhealthy.get("code"), "DETECTOR_UNHEALTHY")

            # Healthy area 1 must continue responding 200 OK
            response_healthy = self.client.get('/api/v1/occupancy/1')
            self.assertEqual(response_healthy.status_code, 200)

    def test_legacy_routes_with_area_query_param(self):
        """Test legacy routes support optional ?areaId= query parameter for areas 1, 2, 3."""
        for area_id in [1, 2, 3]:
            # Test /api/stats?areaId=
            res_stats = self.client.get(f'/api/stats?areaId={area_id}')
            self.assertEqual(res_stats.status_code, 200)

            # Test /api/config?areaId=
            res_cfg = self.client.get(f'/api/config?areaId={area_id}')
            self.assertEqual(res_cfg.status_code, 200)
            cfg_data = json.loads(res_cfg.data)
            self.assertEqual(cfg_data.get("parkingAreaId"), area_id)

            # Test /api/slots?areaId=
            res_slots = self.client.get(f'/api/slots?areaId={area_id}')
            self.assertEqual(res_slots.status_code, 200)
            slots_data = json.loads(res_slots.data)
            self.assertEqual(slots_data.get("parkingAreaId"), area_id)

if __name__ == '__main__':
    unittest.main()
