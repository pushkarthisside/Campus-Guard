from flask import Flask, render_template, Response, jsonify
from flask_socketio import SocketIO
import cv2
import threading
import base64
import time

# Internal project modules
from detector import process_frame
from alerts   import check_and_trigger, get_recent_logs

app = Flask(__name__)
app.config["SECRET_KEY"] = "campusguard_2026_secure"
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# ── Global Hardware & Thread Control ───────────────────────────────────────
camera = None
camera_running = False
camera_thread = None
camera_lock = threading.Lock()

def detection_loop():
    global camera, camera_running

    try:
        with camera_lock:
            if camera is None:
                camera = cv2.VideoCapture(0)
                camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        if not camera.isOpened():
            print("[SYSTEM ERROR] Failed to access webcam hardware.")
            camera_running = False
            return

        print("[SYSTEM INFO] Detection Loop: ACTIVE")
        
        while camera_running:
            success, frame = camera.read()
            if not success:
                time.sleep(0.01)
                continue

            # 1. AI Inference (Zones & Detection are now inside process_frame)
            # This avoids the "Double Drawing" issue
            annotated_frame, detections_info, _ = process_frame(frame)

            # 2. Decision Engine
            sos_active, sos_data, new_log_entry = check_and_trigger(detections_info)

            # 3. Stream Encoding with Fail Protection
            success, buffer = cv2.imencode(".jpg", annotated_frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
            if not success:
                continue

            frame_b64 = base64.b64encode(buffer).decode("utf-8")

            # 4. SocketIO Throttled Dispatch
            socketio.emit("frame_update", {
                "frame": frame_b64,
                "sos_active": sos_active,
                "sos_data": sos_data,
                "detections": detections_info,
                "new_log": new_log_entry
            })

            # Maintains a clean 30 FPS while allowing SocketIO to breathe
            socketio.sleep(0.03)

    except Exception as e:
        print(f"[SYSTEM CRASH] Detection Loop Error: {e}")
    finally:
        with camera_lock:
            if camera:
                camera.release()
                camera = None
        camera_running = False
        print("[SYSTEM INFO] Detection Loop: TERMINATED & Hardware Released")

# ── Flask Routes ─────────────────────────────────────────────────────────────

@app.route("/")
def homepage():
    return render_template("index.html")

@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")

@app.route("/api/logs")
def api_logs():
    return jsonify(get_recent_logs())

# ── SocketIO Events ──────────────────────────────────────────────────────────

@socketio.on("start_camera")
def handle_start_camera():
    global camera_running, camera_thread
    if not camera_running:
        camera_running = True
        # Protection: Ensures we don't spawn multiple parallel AI threads
        camera_thread = socketio.start_background_task(target=detection_loop)
        print("[EVENT] Surveillance sequence triggered by Client.")

@socketio.on("stop_camera")
def handle_stop_camera():
    global camera_running
    camera_running = False
    print("[EVENT] Stop signal received. Cleaning up...")

@socketio.on("connect")
def handle_connect():
    print("[NETWORK] Dashboard connected.")

@socketio.on("disconnect")
def handle_disconnect():
    print("[NETWORK] Dashboard disconnected.")

# ── Execution ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("[SYSTEM] CampusGuard starting at http://localhost:5000")
    # debug=False is CRITICAL here; debug=True spawns two threads and crashes the camera!
    socketio.run(app, host="0.0.0.0", port=5000, debug=False)