import os
from flask import Flask, render_template, Response, jsonify, request
from parking_detector import ParkingDetector

app = Flask(__name__)
detector = ParkingDetector(pos_file='CarParkPos', video_source='carPark.mp4')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(
        detector.generate_frames(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )

@app.route('/api/stats')
def get_stats():
    return jsonify(detector.get_latest_stats())

@app.route('/api/config', methods=['GET', 'POST'])
def handle_config():
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
        "pixel_threshold": detector.pixel_threshold,
        "blur_kernel": detector.blur_kernel,
        "block_size": detector.block_size,
        "c_val": detector.c_val,
        "playback_speed": detector.playback_speed
    })

@app.route('/api/slots', methods=['GET', 'POST'])
def handle_slots():
    if request.method == 'POST':
        data = request.json or {}
        if 'pos_list' in data and isinstance(data['pos_list'], list):
            formatted_pos = [tuple(p) for p in data['pos_list']]
            detector.save_positions(formatted_pos)
            detector.load_positions()
    return jsonify({"pos_list": detector.pos_list})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
