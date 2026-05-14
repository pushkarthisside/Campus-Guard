import threading
from flask import Flask, render_template
from flask_socketio import SocketIO
import cv2
import base64
from detector import process_frame
from alerts import check_and_trigger, stop_alert_sound

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# Thread control
camera_active = threading.Event()
camera_thread = None

def detection_loop():
    cap = cv2.VideoCapture(0)
    print("[SYSTEM] Camera Feed Initiated")
    
    while camera_active.is_set():
        ret, frame = cap.read()
        if not ret: break

        # Process
        processed_frame, detections, _ = process_frame(frame)
        sos_active, sos_data, new_log = check_and_trigger(detections)

        # Encode
        _, buffer = cv2.imencode('.jpg', processed_frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
        frame_b64 = base64.b64encode(buffer).decode('utf-8')

        socketio.emit('frame_update', {
            'frame': frame_b64,
            'sos_active': sos_active,
            'sos_data': sos_data,
            'new_log': new_log
        })
        socketio.sleep(0.01) # Keeps the event loop responsive

    # Cleanup
    cap.release()
    stop_alert_sound()
    print("[SYSTEM] Camera Thread Terminated")

@socketio.on('start_camera')
def handle_start():
    global camera_thread
    if not camera_active.is_set():
        camera_active.set()
        camera_thread = socketio.start_background_task(detection_loop)

@socketio.on('stop_camera')
def handle_stop():
    camera_active.clear() # This kills the loop immediately

@app.route('/')
def index(): return render_template('index.html')

@app.route('/dashboard')
def dashboard(): return render_template('dashboard.html')

if __name__ == '__main__':
    socketio.run(app, debug=False)