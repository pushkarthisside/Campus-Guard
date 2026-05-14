from zones import get_zone_for_bbox, draw_zones
import cv2
import numpy as np
import time
from ultralytics import YOLO
import mediapipe as mp
from deep_sort_realtime.deepsort_tracker import DeepSort

# ─────────────────────────────────────────────────────────────────────────────
# LOAD MODELS
# ─────────────────────────────────────────────────────────────────────────────

yolo_model = YOLO("yolov8n.pt")

# Optional weapon model
# weapon_model = YOLO("models/weapon_model.pt")

# ─────────────────────────────────────────────────────────────────────────────
# MEDIAPIPE POSE
# ─────────────────────────────────────────────────────────────────────────────

mp_pose = mp.solutions.pose

pose_engine = mp_pose.Pose(
    static_image_mode=False,
    model_complexity=0,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

# ─────────────────────────────────────────────────────────────────────────────
# DEEPSORT TRACKER
# ─────────────────────────────────────────────────────────────────────────────

tracker = DeepSort(
    max_age=30,
    n_init=2
)

# ─────────────────────────────────────────────────────────────────────────────
# GLOBAL STATE
# ─────────────────────────────────────────────────────────────────────────────

prev_positions = {}
risk_history = {}

HISTORY_LEN = 10

# ─────────────────────────────────────────────────────────────────────────────
# RISK HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def score_to_color(score):
    if score >= 66:
        return (0, 34, 255)      # RED
    elif score >= 36:
        return (0, 204, 255)     # YELLOW
    else:
        return (0, 255, 136)     # GREEN


def score_to_label(score):
    if score >= 66:
        return "HIGH RISK"
    elif score >= 36:
        return "POTENTIAL RISK"
    else:
        return "SAFE"


def smooth_score(track_id, raw_score):
    if track_id not in risk_history:
        risk_history[track_id] = []

    risk_history[track_id].append(raw_score)

    if len(risk_history[track_id]) > HISTORY_LEN:
        risk_history[track_id].pop(0)

    return int(np.mean(risk_history[track_id]))

# ─────────────────────────────────────────────────────────────────────────────
# POSE EXTRACTION
# ─────────────────────────────────────────────────────────────────────────────

def get_pose_for_person(frame, x1, y1, x2, y2):
    h, w = frame.shape[:2]

    x1 = max(0, int(x1))
    y1 = max(0, int(y1))
    x2 = min(w, int(x2))
    y2 = min(h, int(y2))

    crop = frame[y1:y2, x1:x2]

    if crop.size == 0:
        return None

    try:
        crop_rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
        result = pose_engine.process(crop_rgb)
        return result.pose_landmarks
    except:
        return None

# ─────────────────────────────────────────────────────────────────────────────
# OPTIONAL WEAPON PLACEHOLDER
# ─────────────────────────────────────────────────────────────────────────────

def check_for_weapons(frame, bbox):
    """
    Placeholder weapon logic.
    Integrate actual model later.
    """
    return False

# ─────────────────────────────────────────────────────────────────────────────
# RISK COMPUTATION
#
# FIX: Added `update_pos` parameter (default True).
#   - prev_positions is only written when update_pos=True.
#   - Call with update_pos=False for the "gating" probe so the position
#     isn't consumed before the real scored call, which eliminates the
#     double-call displacement bug where displacement was always 0 on the
#     second invocation.
# ─────────────────────────────────────────────────────────────────────────────

def compute_risk(track_id, bbox, all_bboxes, pose_landmarks, frame_shape, update_pos=True):

    score = 0

    x1, y1, x2, y2 = bbox

    cx = (x1 + x2) / 2
    cy = (y1 + y2) / 2

    box_w = x2 - x1
    box_h = y2 - y1

    # ────────────────────────────────────────────────────────────────────────
    # MOVEMENT DETECTION
    # ────────────────────────────────────────────────────────────────────────

    displacement = 0

    if track_id in prev_positions:

        px, py = prev_positions[track_id]

        displacement = np.sqrt((cx - px) ** 2 + (cy - py) ** 2)

        if displacement > 3:
            score += 10

        # Running
        if displacement > 15:
            score += 20

    # FIX: Only update the stored position when this is the authoritative call.
    # The gating probe passes update_pos=False, so the position is preserved
    # for the final scored call which passes update_pos=True (the default).
    if update_pos:
        prev_positions[track_id] = (cx, cy)

    # ────────────────────────────────────────────────────────────────────────
    # PROXIMITY DETECTION
    # ────────────────────────────────────────────────────────────────────────

    for other_bbox in all_bboxes:

        ox1, oy1, ox2, oy2 = other_bbox

        ocx = (ox1 + ox2) / 2
        ocy = (oy1 + oy2) / 2

        dist = np.sqrt((cx - ocx) ** 2 + (cy - ocy) ** 2)

        if 5 < dist < box_w * 1.5:
            score += 30
            break

    # ────────────────────────────────────────────────────────────────────────
    # AGGRESSIVE POSE DETECTION
    # ────────────────────────────────────────────────────────────────────────

    if pose_landmarks:

        try:
            lm = pose_landmarks.landmark

            left_wrist = lm[mp_pose.PoseLandmark.LEFT_WRIST]
            right_wrist = lm[mp_pose.PoseLandmark.RIGHT_WRIST]

            left_shoulder = lm[mp_pose.PoseLandmark.LEFT_SHOULDER]
            right_shoulder = lm[mp_pose.PoseLandmark.RIGHT_SHOULDER]

            nose = lm[mp_pose.PoseLandmark.NOSE]

            left_arm_raised = left_wrist.y < left_shoulder.y
            right_arm_raised = right_wrist.y < right_shoulder.y

            if left_arm_raised or right_arm_raised:
                score += 40

            avg_shoulder_y = (
                left_shoulder.y + right_shoulder.y
            ) / 2

            if nose.y > avg_shoulder_y + 0.1:
                score += 15

        except:
            pass

    # ────────────────────────────────────────────────────────────────────────
    # FALLEN PERSON DETECTION
    # ────────────────────────────────────────────────────────────────────────

    aspect_ratio = box_w / (box_h + 1e-5)

    if aspect_ratio > 1.6:
        score += 60

    return min(score, 100)

# ─────────────────────────────────────────────────────────────────────────────
# MAIN FRAME PROCESSOR
# ─────────────────────────────────────────────────────────────────────────────

def process_frame(frame):

    # ────────────────────────────────────────────────────────────────────────
    # YOLO DETECTION
    # ────────────────────────────────────────────────────────────────────────

    results = yolo_model(
        frame,
        classes=[0],
        verbose=False
    )[0]

    raw_detections = []

    for box in results.boxes:

        x1, y1, x2, y2 = box.xyxy[0].tolist()

        conf = float(box.conf[0])

        if conf < 0.4:
            continue

        raw_detections.append(
            (
                [x1, y1, x2 - x1, y2 - y1],
                conf,
                "person"
            )
        )

    # ────────────────────────────────────────────────────────────────────────
    # TRACKING
    # ────────────────────────────────────────────────────────────────────────

    tracks = tracker.update_tracks(
        raw_detections,
        frame=frame
    )

    confirmed_bboxes = []

    for track in tracks:

        if not track.is_confirmed():
            continue

        x1, y1, x2, y2 = track.to_ltrb()

        confirmed_bboxes.append(
            [x1, y1, x2, y2]
        )

    detections_info = []
    frame = draw_zones(frame)

    any_red = False

    # ────────────────────────────────────────────────────────────────────────
    # PROCESS EACH TRACK
    # ────────────────────────────────────────────────────────────────────────

    for track in tracks:

        if not track.is_confirmed():
            continue

        track_id = track.track_id

        x1, y1, x2, y2 = track.to_ltrb()
        zone_name = get_zone_for_bbox(x1, y1, x2, y2)

        # ────────────────────────────────────────────────────────────────────
        # PERFORMANCE GATE
        #
        # FIX: Pass update_pos=False so prev_positions is NOT mutated here.
        # The displacement calculated in the final scored call below will
        # therefore use the correct previous-frame position, preserving
        # accurate "Running" detection.
        # ────────────────────────────────────────────────────────────────────

        base_score = compute_risk(
            track_id,
            [x1, y1, x2, y2],
            confirmed_bboxes,
            None,
            frame.shape,
            update_pos=False       # <── FIX: don't consume the position yet
        )

        # Only run expensive pose inference if there is already some activity
        pose_lm = None
        if base_score >= 15:
            pose_lm = get_pose_for_person(
                frame,
                x1,
                y1,
                x2,
                y2
            )

        # ────────────────────────────────────────────────────────────────────
        # WEAPON PLACEHOLDER
        # ────────────────────────────────────────────────────────────────────

        is_weapon = check_for_weapons(
            frame,
            [x1, y1, x2, y2]
        )

        # ────────────────────────────────────────────────────────────────────
        # FINAL SCORE
        #
        # FIX: This is the single authoritative call — update_pos defaults to
        # True, so prev_positions is written exactly once per track per frame.
        # Displacement math is now correct for every frame.
        # ────────────────────────────────────────────────────────────────────

        raw_score = compute_risk(
            track_id,
            [x1, y1, x2, y2],
            confirmed_bboxes,
            pose_lm,               # real pose landmarks (or None)
            frame.shape,
            update_pos=True        # <── FIX: write position exactly once
        )

        if is_weapon:
            raw_score += 50

        raw_score = min(raw_score, 100)

        score = smooth_score(track_id, raw_score)

        color = score_to_color(score)

        label = score_to_label(score)

        if score >= 66:
            any_red = True

        # ────────────────────────────────────────────────────────────────────
        # DRAW BOX
        # ────────────────────────────────────────────────────────────────────

        cv2.rectangle(
            frame,
            (int(x1), int(y1)),
            (int(x2), int(y2)),
            color,
            2
        )

        # ────────────────────────────────────────────────────────────────────
        # LABEL
        # ────────────────────────────────────────────────────────────────────

        tag = f"ID{track_id} | {score}% | {label}"

        tag_y = max(int(y1) - 10, 20)

        cv2.putText(
            frame,
            tag,
            (int(x1), tag_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            color,
            2
        )

        detections_info.append({
            "track_id": int(track_id),
            "zone": zone_name,
            "score": score,
            "label": label,
            "bbox": [
                int(x1),
                int(y1),
                int(x2),
                int(y2)
            ]
        })

    # ────────────────────────────────────────────────────────────────────────
    # CLEANUP OLD TRACKS
    # ────────────────────────────────────────────────────────────────────────

    active_ids = {
        track.track_id
        for track in tracks
        if track.is_confirmed()
    }

    for tid in list(prev_positions.keys()):
        if tid not in active_ids:
            prev_positions.pop(tid, None)

    for tid in list(risk_history.keys()):
        if tid not in active_ids:
            risk_history.pop(tid, None)

    return frame, detections_info, any_red

if __name__ == "__main__":

    cap = cv2.VideoCapture(0)

    while True:

        ret, frame = cap.read()

        if not ret:
            break

        processed_frame, detections, any_red = process_frame(frame)

        cv2.imshow("CampusGuard Detector Test", processed_frame)

        key = cv2.waitKey(1)

        if key == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()