import os
import time
import atexit
from flask import Flask, render_template, Response, jsonify, request
from parking_detector import ParkingDetectorManager

app = Flask(__name__)
detector_manager = ParkingDetectorManager(config_file='parking_areas.json')

# Clean shutdown handler
atexit.register(lambda: detector_manager.stop_all())

# Helper to retrieve detector for legacy routes
def get_target_detector(default_area_id=1):
    area_param = request.args.get('areaId') or request.args.get('parkingAreaId') or str(default_area_id)
    try:
        area_id = int(area_param)
    except (ValueError, TypeError):
        area_id = default_area_id

    detector = detector_manager.get_detector(area_id)
    if detector is None:
        detector = detector_manager.get_detector(default_area_id)
    return detector

# In-memory stores for legacy demo vehicles and bookings
vehicles_db = [
    {"id": 1, "vehicleNumber": "KL05AB1234", "vehicleType": "Car"},
    {"id": 2, "vehicleNumber": "KL05XY5678", "vehicleType": "SUV"}
]

bookings_db = []
booking_id_counter = 100

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    detector = get_target_detector()
    if detector is None or not detector.is_healthy:
        return jsonify({"error": "Video feed unavailable for requested area"}), 503

    return Response(
        detector.generate_frames(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )

# --- OFFICIAL AI-1 REST API: DISCOVERY & OCCUPANCY DETECTION ---

@app.route('/api/v1/areas', methods=['GET'])
def get_v1_areas():
    """
    Official AI-1 HTTP API Endpoint for backend area discovery.
    Returns array of all configured parking areas with actual totalSlots.
    """
    areas_info = detector_manager.get_all_areas_info()
    return jsonify(areas_info), 200

@app.route('/api/v1/occupancy/<path:parking_area_id>', methods=['GET'])
def get_v1_occupancy(parking_area_id):
    """
    Official AI-1 HTTP API Endpoint for Spring Boot backend integration.
    Returns real-time physical slot occupancy observed by computer vision.
    AI-1 physical statuses: AVAILABLE, OCCUPIED. (Does NOT return RESERVED).
    """
    try:
        area_id = int(parking_area_id)
    except (ValueError, TypeError):
        return jsonify({
            "error": "Invalid parkingAreaId. Must be a positive integer.",
            "code": "INVALID_PARKING_AREA_ID"
        }), 400

    if area_id <= 0:
        return jsonify({
            "error": "Invalid parkingAreaId. Must be a positive integer.",
            "code": "INVALID_PARKING_AREA_ID"
        }), 400

    detector = detector_manager.get_detector(area_id)
    if detector is None:
        return jsonify({
            "error": f"Parking area with ID {area_id} not found or not configured.",
            "code": "PARKING_AREA_NOT_FOUND"
        }), 404

    if not detector.is_healthy:
        return jsonify({
            "error": f"Detector for parking area {area_id} failed startup check: {detector.health_error}",
            "code": "DETECTOR_UNHEALTHY"
        }), 500

    stats = detector.get_latest_physical_stats()
    if stats is None:
        return jsonify({
            "error": "Occupancy detection service is temporarily unavailable.",
            "code": "DETECTION_UNAVAILABLE"
        }), 503

    return jsonify(stats), 200

# --- LEGACY DEMO UI & BACKWARD COMPATIBILITY ENDPOINTS ---

@app.route('/api/parking-areas/<int:parking_area_id>', methods=['GET'])
def get_parking_area_details(parking_area_id):
    detector = detector_manager.get_detector(parking_area_id) or get_target_detector(1)
    if detector is None or not detector.is_healthy:
        return jsonify({"error": "Parking area telemetry unavailable"}), 503

    stats = detector.get_latest_stats()
    total = stats.get('total_slots', len(detector.pos_list))
    available = stats.get('available_slots', 0)
    occupied = stats.get('occupied_slots', 0)
    occupancy_pct = int(round(stats.get('occupancy_rate', 0.0)))

    return jsonify({
        "id": detector.area_id,
        "name": detector.name,
        "distanceMeters": 280,
        "hourlyRate": 50,
        "totalSlots": total,
        "availableSlots": available,
        "occupiedSlots": occupied,
        "occupancyPercentage": occupancy_pct
    })

@app.route('/api/parking-areas/<int:parking_area_id>/slots', methods=['GET'])
def get_parking_area_slots(parking_area_id):
    detector = detector_manager.get_detector(parking_area_id) or get_target_detector(1)
    if detector is None or not detector.is_healthy:
        return jsonify({"error": "Parking area slots unavailable"}), 503

    stats = detector.get_latest_stats()
    formatted_slots = []
    
    for s in stats.get('slots', []):
        formatted_slots.append({
            "id": s["id"],
            "slotNumber": s.get("slotNumber", f"A{s['id']:02d}"),
            "status": s.get("status", "OCCUPIED" if s["occupied"] else "AVAILABLE")
        })

    return jsonify({
        "parkingAreaId": detector.area_id,
        "slots": formatted_slots
    })

@app.route('/api/vehicles', methods=['GET', 'POST'])
def handle_vehicles():
    if request.method == 'POST':
        data = request.json or {}
        v_num = data.get('vehicleNumber', '').strip()
        v_type = data.get('vehicleType', 'Car').strip()
        
        if not v_num:
            return jsonify({"error": "Vehicle number is required"}), 400
            
        new_vehicle = {
            "id": len(vehicles_db) + 1,
            "vehicleNumber": v_num,
            "vehicleType": v_type
        }
        vehicles_db.append(new_vehicle)
        return jsonify(new_vehicle), 201

    return jsonify(vehicles_db)

@app.route('/api/bookings', methods=['GET', 'POST'])
def handle_bookings():
    global booking_id_counter
    if request.method == 'POST':
        data = request.json or {}
        p_area_id = int(data.get('parkingAreaId', 1))
        p_slot_id = int(data.get('parkingSlotId', 1))
        v_id = int(data.get('vehicleId', 1))
        duration = int(data.get('durationHours', 1))

        rate_per_hour = 50
        authoritative_amount = rate_per_hour * duration

        booking_id_counter += 1
        booking = {
            "bookingId": booking_id_counter,
            "parkingAreaId": p_area_id,
            "parkingSlotId": p_slot_id,
            "vehicleId": v_id,
            "durationHours": duration,
            "amount": authoritative_amount,
            "status": "PENDING_PAYMENT",
            "createdAt": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        detector = detector_manager.get_detector(p_area_id) or get_target_detector(1)
        if detector:
            detector.reserve_slot(p_slot_id)

        bookings_db.append(booking)
        return jsonify(booking), 201

    return jsonify(bookings_db)

@app.route('/api/stats')
def get_stats():
    detector = get_target_detector()
    if detector is None or not detector.is_healthy:
        return jsonify({"error": "Detector unavailable for requested area"}), 503
    return jsonify(detector.get_latest_stats())

@app.route('/api/config', methods=['GET', 'POST'])
def handle_config():
    detector = get_target_detector()
    if detector is None:
        return jsonify({"error": "Detector not found"}), 404

    if request.method == 'POST':
        data = request.json or {}
        if 'pixel_threshold' in data:
            detector.pixel_threshold = int(data['pixel_threshold'])
        if 'blur_kernel' in data:
            detector.blur_kernel = int(data['blur_kernel'])
        if 'block_size' in data:
            detector.block_size = int(data['block_size'])
        if 'c_val' in data:
            detector.c_val = int(data['c_val'])
        if 'playback_speed' in data:
            detector.playback_speed = float(data['playback_speed'])
            
    return jsonify({
        "parkingAreaId": detector.area_id,
        "pixel_threshold": detector.pixel_threshold,
        "blur_kernel": detector.blur_kernel,
        "block_size": detector.block_size,
        "c_val": detector.c_val,
        "playback_speed": detector.playback_speed
    })

@app.route('/api/slots', methods=['GET', 'POST'])
def handle_slots():
    detector = get_target_detector()
    if detector is None:
        return jsonify({"error": "Detector not found"}), 404

    if request.method == 'POST':
        data = request.json or {}
        if 'pos_list' in data and isinstance(data['pos_list'], list):
            formatted_pos = [tuple(p) for p in data['pos_list']]
            detector.save_positions(formatted_pos)
            detector.load_positions()
    return jsonify({
        "parkingAreaId": detector.area_id,
        "pos_list": detector.pos_list
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
