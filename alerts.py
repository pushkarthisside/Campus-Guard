import pygame
import datetime
import os
import time

# ── Safe Sound Initialization ───────────────────────────────────────────────
try:
    pygame.mixer.init()
    MIXER_READY = True
except Exception as e:
    print(f"[SYSTEM] Audio initialization failed: {e}")
    MIXER_READY = False

ALERT_SOUND_PATH = os.path.join("static", "sounds", "alert.mp3")
alert_playing    = False
alert_log        = []  

# Cooldown to prevent logging the same ID every single frame
last_alert_time  = {} 
LOG_COOLDOWN     = 5  

def play_alert_sound():
    global alert_playing
    if MIXER_READY and not alert_playing:
        if os.path.exists(ALERT_SOUND_PATH):
            try:
                pygame.mixer.music.load(ALERT_SOUND_PATH)
                pygame.mixer.music.play(-1)
                alert_playing = True
            except Exception:
                pass # Silent fail to prevent crash during demo

def stop_alert_sound():
    global alert_playing
    if MIXER_READY and alert_playing:
        pygame.mixer.music.stop()
        alert_playing = False

def log_alert(threat_type, zone, score, track_id):
    """Logs the alert only if the cooldown period has passed."""
    curr = time.time()
    if track_id not in last_alert_time or (curr - last_alert_time[track_id] > LOG_COOLDOWN):
        entry = {
            "time":     datetime.datetime.now().strftime("%H:%M:%S"),
            "threat":   threat_type,
            "zone":     zone,
            "score":    score,
            "track_id": track_id,
            "level":    "🔴 HIGH" if score >= 66 else "🟡 MEDIUM"
        }
        alert_log.append(entry)
        last_alert_time[track_id] = curr
        if len(alert_log) > 50: alert_log.pop(0)
        return entry
    return None

def get_threat_type(score):
    if score >= 90: return "Weapon / Assault Detected"
    if score >= 75: return "Aggressive Behavior"
    return "Physical Altercation"

def check_and_trigger(detections_info):
    """
    Scans all detections, selects the highest risk threat, 
    and triggers SOS if score >= 66.
    """
    sos_active    = False
    highest_det   = None
    max_red_score = -1

    # 1. Find the MOST dangerous person in the frame
    for det in detections_info:
        score = det.get("score", 0)
        if score >= 66:
            sos_active = True
            if score > max_red_score:
                max_red_score = score
                highest_det = det

    # 2. Trigger SOS only for the highest risk found
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

    # 3. If no RED threats, kill the sound
    stop_alert_sound()
    return False, None, None

def get_recent_logs(n=20):
    return list(reversed(alert_log[-n:]))