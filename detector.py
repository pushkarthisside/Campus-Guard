import cv2
import numpy as np
import time
from ultralytics import YOLO
from deep_sort_realtime.deepsort_tracker import DeepSort

# DIRECT IMPORT FIX: Bypass the .solutions attribute error
try:
    import mediapipe.python.solutions.pose as mp_pose
except Exception:
    mp_pose = None
    print("[SYSTEM] MediaPipe Direct Import Failed")

# 1. Faster Model: yolov8n is roughly 3x faster than yolov8s
yolo_model = YOLO("yolov8n.pt")

# Tracker setup: shorter max_age for quicker cleanup
tracker = DeepSort(max_age=15, n_init=2)

# Pose Engine Setup
pose_engine = None
if mp_pose:
    pose_engine = mp_pose.Pose(
        static_image_mode=False,
        model_complexity=0, # 0 is optimized for speed
        min_detection_confidence=0.5
    )

# Persistent State
prev_positions = {}
fast_move_counter = {}

def process_frame(frame):
    # YOLO Detection
    results = yolo_model(frame, classes=[0], conf=0.5, verbose=False)[0]
    raw_detections = []

    for box in results.boxes:
        x1, y1, x2, y2 = box.xyxy[0].tolist()
        conf = float(box.conf[0])
        raw_detections.append(([x1, y1, x2-x1, y2-y1], conf, "person"))

    # Tracking
    tracks = tracker.update_tracks(raw_detections, frame=frame)
    detections_info = []

    for track in tracks:
        if not track.is_confirmed():
            continue
        
        track_id = track.track_id
        x1, y1, x2, y2 = map(int, track.to_ltrb())
        
        # Movement Score with fast-move counter
        score = 20
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2

        if track_id in prev_positions:
            dist = np.hypot(cx - prev_positions[track_id][0], cy - prev_positions[track_id][1])
            if dist > 20:
                fast_move_counter[track_id] = fast_move_counter.get(track_id, 0) + 1
            else:
                fast_move_counter[track_id] = 0  # reset if not fast

            # Only score high if fast for 3+ consecutive frames
            if fast_move_counter.get(track_id, 0) >= 3:
                score += 40
            elif dist > 8:
                score += 15

        prev_positions[track_id] = (cx, cy)

        # Drawing (No Zones)
        color = (0, 255, 0) if score < 75 else (0, 0, 255)
        label = "SAFE" if score < 75 else "HIGH RISK"
        
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        cv2.putText(frame, f"ID:{track_id} {score}% {label}", (x1, y1-10), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        detections_info.append({
            "track_id": track_id,
            "score": score,
            "threat": "Movement Detected" if score > 30 else "Normal",
            "zone": "Floor", # Simplified
            "bbox": [x1, y1, x2, y2]
        })

    return frame, detections_info, any(d['score'] >= 75 for d in detections_info)