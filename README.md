# 🅿️ SMART URBAN PARKING SOLUTION — AI-1: Multi-Area Parking Slot Occupancy Detection

> **AI-1 Microservice**: Real-time multi-area OpenCV computer vision engine for monitoring CCTV parking video streams, matching area-specific slot bounding boxes (`CarParkPos`), and serving physical occupancy status via REST API to the Spring Boot backend.

---

## 🏗️ Multi-Area Architecture & AI-1 Boundaries

AI-1 supports monitoring multiple parking areas concurrently. Each parking area runs on its own isolated background detector thread with its own video source file, slot coordinate file (`CarParkPos`), pixel occupancy threshold, and looping configuration.

```
                               React/Vite Frontend
                                        │
                                        ▼ (REST API)
                              Spring Boot Backend
                                        │
                     ┌──────────────────┴──────────────────┐
                     ▼                                     ▼
              MySQL Database                     AI Microservices
                                                           │
                                                           ▼
                                            AI-1 Service (Flask @ :5000)
                                                           │
                                                parking_areas.json Config
                                                           │
                            ┌──────────────────────────────┼──────────────────────────────┐
                            ▼                              ▼                              ▼
                  Area 1: Main Lot               Area 2: North Annex            Area 3: East Plaza
                  (carPark.mp4,                  (carPark2.mp4,                 (carPark3.mp4,
                   CarParkPos - 69 slots)         CarParkPos2 - 30 slots)        CarParkPos3 - 45 slots)
```

### 🛑 AI-1 Responsibilities & Constraints
- **AI-1 Role**: Reports **ONLY** observed physical occupancy detected from the video streams.
- **AI-1 MUST NOT**:
  - Create bookings or reserve parking slots.
  - Process payments, generate QR codes, or verify QR codes.
  - Perform user/vehicle check-in or manage user/vehicle entities.
  - Access or modify MySQL database tables.
  - Return `RESERVED` status. (Physical statuses are strictly `AVAILABLE` or `OCCUPIED`).
- **Spring Boot Authority**: Spring Boot is authoritative for users, vehicles, parking areas, slots, bookings, payments, reservations, check-in, and MySQL state.

---

## ⚙️ Configuration File (`parking_areas.json`)

All parking areas are registered in `parking_areas.json` at startup:

```json
[
  {
    "parkingAreaId": 1,
    "name": "City Mall Main Lot",
    "videoSource": "carPark.mp4",
    "posFile": "CarParkPos",
    "pixelThreshold": 900,
    "videoLoop": true
  },
  {
    "parkingAreaId": 2,
    "name": "North Annex Parking",
    "videoSource": "carPark2.mp4",
    "posFile": "CarParkPos2",
    "pixelThreshold": 850,
    "videoLoop": true
  },
  {
    "parkingAreaId": 3,
    "name": "East Plaza Garage",
    "videoSource": "carPark3.mp4",
    "posFile": "CarParkPos3",
    "pixelThreshold": 950,
    "videoLoop": true
  }
]
```

> [!NOTE]
> **Threshold Tuning**: `pixelThreshold` is empirically tuned per camera view due to varying camera distance, angle, and lighting. When swapping in new real video files for `carPark2.mp4` or `carPark3.mp4`, re-tune `pixelThreshold` for that specific video area.

---

## 🔌 AI-1 Official REST APIs

### 1. Area Discovery API: `GET /api/v1/areas`

Returns a dynamic listing of all configured parking areas. `totalSlots` is read dynamically from each area's loaded coordinate file.

#### Response Example (200 OK)
```json
[
  {
    "id": 1,
    "name": "City Mall Main Lot",
    "totalSlots": 69,
    "isHealthy": true
  },
  {
    "id": 2,
    "name": "North Annex Parking",
    "totalSlots": 30,
    "isHealthy": true
  },
  {
    "id": 3,
    "name": "East Plaza Garage",
    "totalSlots": 45,
    "isHealthy": true
  }
]
```

---

### 2. Slot Occupancy API: `GET /api/v1/occupancy/{parkingAreaId}`

Retrieves real-time physical slot occupancy for the requested parking area.

#### Request Example
```bash
curl -X GET http://localhost:5000/api/v1/occupancy/1
```

#### Response Contract (200 OK)
```json
{
  "parkingAreaId": 1,
  "name": "City Mall Main Lot",
  "timestamp": "2026-09-22T11:45:00Z",
  "source": "carPark.mp4",
  "totalSlots": 69,
  "availableSlots": 42,
  "occupiedSlots": 27,
  "occupancyPercentage": 39.13,
  "slots": [
    {
      "slotId": 1,
      "slotNumber": "A01",
      "status": "AVAILABLE"
    },
    {
      "slotId": 2,
      "slotNumber": "A02",
      "status": "OCCUPIED"
    }
  ]
}
```

> [!IMPORTANT]
> **Timestamp & Video Looping Semantics**:
> When `videoLoop: true` is configured, `timestamp` represents the ISO 8601 UTC time when the last video frame was processed. Downstream consumers (Spring Boot, AI-3) should interpret `timestamp` as frame telemetry time.

#### HTTP Error Status Codes
| Code | Reason | Description |
| :--- | :--- | :--- |
| **200** | OK | Successfully returned slot occupancy. |
| **400** | Bad Request | `parkingAreaId` is invalid (e.g. `<= 0` or malformed). |
| **404** | Not Found | Parking area ID not registered in `parking_areas.json`. |
| **500** | Internal Error | Area detector failed startup health check (e.g. missing video file). |

---

## 🛠️ How to Add a New Parking Area

To add a new video stream / parking area to AI-1:

### Step 1: Place Video File
Place the recorded `.mp4` video file in the project folder (e.g., `carPark4.mp4`).

### Step 2: Run Interactive Slot-Coordinate Marking Tool
Use the CLI tool to open the first frame of the new video and mark parking slot bounding boxes:

```powershell
.\.venv\Scripts\python.exe ParkingSpacePicker.py --video carPark4.mp4 --output CarParkPos4
```
- **Left-click**: Add a new parking slot bounding box.
- **Right-click**: Delete bounding box under cursor.
- **Press 'q' or ESC**: Save coordinates to `CarParkPos4` and exit.

### Step 3: Register Area in `parking_areas.json`
Add a new entry to `parking_areas.json`:

```json
{
  "parkingAreaId": 4,
  "name": "South Bay Deck",
  "videoSource": "carPark4.mp4",
  "posFile": "CarParkPos4",
  "pixelThreshold": 900,
  "videoLoop": true
}
```

### Step 4: Restart Server
Restart Flask server (`python server.py`). The new area will be automatically verified at startup and served at `GET /api/v1/occupancy/4`.

---

## ☕ Spring Boot Integration Guide

1. **Discovery**: Spring Boot calls `GET http://<ai1-host>:5000/api/v1/areas` to discover all active parking area IDs and slot capacities.
2. **Occupancy Fetch**: Spring Boot calls `GET http://<ai1-host>:5000/api/v1/occupancy/{id}` for each area.
3. **Status Merge Logic**:
   - AI-1 physical status: `AVAILABLE` or `OCCUPIED`.
   - Spring Boot database status: `RESERVED` (if slot has active booking/reservation).
   - Final state exposed to React frontend:
     - Active reservation in MySQL -> `RESERVED`
     - Else if AI-1 physical status is `OCCUPIED` -> `OCCUPIED`
     - Else -> `AVAILABLE`

---

## 🚀 Setup, Run & Test

### Start Flask Server
```powershell
.\.venv\Scripts\python.exe server.py
```

### Legacy Route Backward Compatibility
Legacy routes default to `areaId=1` and accept an optional `?areaId=` query parameter:
- Video Stream Area 1: `http://localhost:5000/video_feed?areaId=1`
- Video Stream Area 2: `http://localhost:5000/video_feed?areaId=2`
- Telemetry Stats Area 3: `http://localhost:5000/api/stats?areaId=3`

### Run Automated Unit Tests
```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
```
