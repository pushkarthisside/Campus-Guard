import pygame
import datetime
import os
import time

# ── Sound Init ────────────────────────────────────────────────────────────────
try:
    pygame.mixer.init()
    MIXER_READY = True
except Exception as e:
    print(f"[SYSTEM] Audio init failed: {e}")
    MIXER_READY = False

ALERT_SOUND_PATH = os.path.join("static", "sounds", "alert.mp3")
alert_playing    = False
alert_log        = []
last_alert_time  = {}

# 5 second cooldown — same person won't spam the log every frame
LOG_COOLDOWN = 5

# ── Sound Controls ────────────────────────────────────────────────────────────
def play_alert_sound():
    global alert_playing
    if MIXER_READY and not alert_playing:
        if os.path.exists(ALERT_SOUND_PATH):
            try:
                pygame.mixer.music.load(ALERT_SOUND_PATH)
                pygame.mixer.music.play(-1)
                alert_playing = True
            except Exception:
                pass

def stop_alert_sound():
    """Called by app.py on stop_camera AND by check_and_trigger when no threat."""
    global alert_playing
    if MIXER_READY and alert_playing:
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass
    # Always reset the flag, even if mixer wasn't ready, so state stays clean
    alert_playing = False

# ── Logging ───────────────────────────────────────────────────────────────────
def log_alert(threat_type, zone, score, track_id):
    curr = time.time()
    if track_id not in last_alert_time or (curr - last_alert_time[track_id] > LOG_COOLDOWN):
        entry = {
            "time":     datetime.datetime.now().strftime("%H:%M:%S"),
            "threat":   threat_type,
            "zone":     zone,
            "score":    score,
            "track_id": track_id,
            "level":    "🔴 HIGH" if score >= 60 else "🟡 MEDIUM"
        }
        alert_log.append(entry)
        last_alert_time[track_id] = curr
        if len(alert_log) > 50:
            alert_log.pop(0)
        return entry
    return None

def get_threat_type(score):
    if score >= 90: return "Weapon / Assault Detected"
    if score >= 78: return "Aggressive Behavior"
    return "Physical Altercation"

# ── Main Trigger ──────────────────────────────────────────────────────────────
def check_and_trigger(detections_info):
    """
    Raised SOS threshold from 66 → 78.
    At 66 the scorer was firing on normal movement (someone walking fast,
    two people standing close). 78 requires actual combined signals.
    """
    sos_active    = False
    highest_det   = None
    max_red_score = -1

    for det in detections_info:
        score = det.get("score", 0)
        if score >= 78:                      # <-- was 66, raised to stop false alarms
            sos_active = True
            if score > max_red_score:
                max_red_score = score
                highest_det   = det

    if sos_active and highest_det:
        track_id = highest_det["track_id"]
        zone     = highest_det.get("zone", "Unknown")
        threat   = get_threat_type(max_red_score)

        sos_data = {
            "track_id": track_id,
            "score":    max_red_score,
            "threat":   threat,
            "zone":     zone,
            "time":     datetime.datetime.now().strftime("%H:%M:%S")
        }

        new_log_entry = log_alert(threat, zone, max_red_score, track_id)
        play_alert_sound()
        return True, sos_data, new_log_entry

    # No threat — stop sound immediately
    stop_alert_sound()
    return False, None, None

def get_recent_logs(n=20):
    return list(reversed(alert_log[-n:]))