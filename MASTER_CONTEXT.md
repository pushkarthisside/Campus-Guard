# MASTER_CONTEXT.md — CampusGuard
## Smart Surveillance Threat Detection System

> ⚠️ PASTE THIS FILE AT THE START OF EVERY NEW AI CHAT SESSION.
> This is the single source of truth for the entire project.

---

## 1. PROJECT OVERVIEW

**Project Name:** CampusGuard  
**Full Name:** Smart Surveillance Threat Detection System  
**Type:** Local real-time AI webcam surveillance dashboard  
**Purpose:** Detect threats in a live camera feed, assign per-person risk scores, and trigger visual + audio alerts  
**Deployment:** Runs 100% locally on laptop — NO cloud, NO Vercel, NO paid APIs  
**Demo Context:** College/university tech exhibition — judges are professors and peers  

---

## 2. USER FLOW

### Screen 1: Homepage (Screensaver)
- Dark themed UI with animated background (slow moving grid or pulse effect)
- Project name: **CampusGuard**
- Tagline: *"AI-Powered Real-Time Campus Threat Detection"*
- Single button: **[Launch Surveillance]**
- Clicking the button navigates to Screen 2

### Screen 2: Surveillance Dashboard
- Live webcam feed fills the main area
- Bounding boxes drawn over every detected person/object
- Each box is colored + shows a risk % (updates every frame)
- Bottom panel: scrolling **Threat Log** (timestamp + zone + threat type)
- Top bar: camera name (CAM-01), live clock, REC indicator

### On RED Alert Trigger:
- Webcam feed shrinks to left ~65% of screen (stays live, does NOT close)
- Animated vertical sidebar slides in from the right showing:
  - 🚨 SOS TRIGGERED
  - Threat type detected
  - Zone name
  - Timestamp
  - Notifying: Campus Security ✓ / Local Police ⟳ / Admin Office ⟳ (with ping animation)
  - Optional: 1-line AI-generated incident summary (Gemini free tier)
- Alert sound plays (Pygame)
- When threat clears → sidebar slides out, feed returns to full size

---

## 3. RISK SCORING SYSTEM (PER PERSON, PER FRAME)

Each detected person starts at 0% risk each frame. Points are added based on behaviour:

| Behaviour Detected | Points Added |
|---|---|
| Moving (not stationary) | +10% |
| Running (high bounding box displacement) | +20% |
| Within close proximity of another person | +30% |
| Aggressive pose (arms raised, body bent forward) | +40% |
| Weapon detected in their bounding box region | +50% |
| Person on ground / fallen | +60% |

**Color thresholds:**
- 0–35% → 🟢 GREEN box
- 36–65% → 🟡 YELLOW box
- 66–100% → 🔴 RED box → triggers SOS sidebar

Each person in the frame gets their own independent box + score.  
Example: One person at 90% RED, another at 30% GREEN in the same frame.

---

## 4. WHAT IT DETECTS

| Behaviour | Method | Expected Accuracy |
|---|---|---|
| Person present | YOLOv8n (COCO) | 95%+ |
| Running | Bounding box displacement speed across frames | 85%+ |
| Chasing | Two people, one following same trajectory | 80%+ |
| Fighting / punching / kicking | MediaPipe Pose — arm angles + proximity | 70–75% |
| Stabbing | Weapon detection + arm angle at close range | 70%+ |
| Erratic behaviour | Rapid direction changes via motion vector | 70%+ |
| Weapons (gun, knife, stick) | Pre-trained weapon detection model (GitHub) | 80%+ |

---

## 5. TECH STACK (ALL FREE, ALL LOCAL)

| Layer | Tool | Purpose |
|---|---|---|
| Object Detection | YOLOv8n (Ultralytics) | Detect persons + weapons |
| Pose Estimation | MediaPipe Pose | Detect body keypoints for action classification |
| Video Handling | OpenCV (cv2) | Webcam capture, frame processing, drawing boxes |
| Backend Server | Python + Flask | Serves the dashboard, handles detection loop |
| Real-time Comms | Flask-SocketIO | Pushes detection events to frontend in real time |
| Frontend | HTML + CSS + JS | Dashboard UI, animations, sidebar alert |
| Alert Sound | Pygame | Plays alarm audio on RED trigger |
| AI Summary (optional) | Gemini free tier API | Generates 1-line incident description on RED |

**Python version:** 3.10+  
**Key packages:** ultralytics, mediapipe, opencv-python, flask, flask-socketio, pygame  

---

## 6. FILE STRUCTURE

```
campusguard/
│
├── app.py                  # Flask server, SocketIO, main entry point
├── detector.py             # YOLOv8 + MediaPipe detection logic, risk scoring
├── zones.py                # Zone definitions (Gate, Corridor, Lab etc.)
├── alerts.py               # Alert rules, threshold checks, sound trigger
├── requirements.txt        # All pip dependencies
│
├── models/
│   └── yolov8n.pt          # Base YOLO model (auto-downloads)
│   └── weapon_model.pt     # Pre-trained weapon detection model (from GitHub)
│
├── static/
│   ├── css/
│   │   └── style.css       # All styles
│   ├── js/
│   │   └── main.js         # SocketIO client, UI logic, sidebar animation
│   └── sounds/
│       └── alert.mp3       # Alarm sound
│
├── templates/
│   ├── index.html          # Homepage / screensaver
│   └── dashboard.html      # Surveillance dashboard
│
└── MASTER_CONTEXT.md       # This file
```

---

## 7. BUILD ORDER

Build files in this exact order to avoid dependency issues:

1. `detector.py` — Core detection + risk scoring (no UI dependency)
2. `zones.py` — Zone coordinate definitions
3. `alerts.py` — Alert logic, sound trigger
4. `app.py` — Flask routes + SocketIO events
5. `templates/index.html` — Homepage UI
6. `templates/dashboard.html` + `static/js/main.js` + `static/css/style.css` — Dashboard UI

---

## 8. UI DESIGN RULES

- **Theme:** Dark — background #0a0a0f, panels #0f1117
- **Accent colors:** Green #00ff88, Yellow #ffcc00, Red #ff2244
- **Font:** Monospace / terminal feel (suggests real security software)
- **Animations:** Sidebar slides in from right on RED, ping animation for authority notifications
- **No flashy gradients** — clean, utilitarian, like actual CCTV software
- **Bounding boxes:** Drawn directly on the OpenCV frame, color = risk level, % shown on top-left of box

---

## 9. DEMO SCENARIOS (PRE-TEST THESE ONLY)

| Scenario | What to do in front of camera | Expected output |
|---|---|---|
| 1. Safe | Stand still alone | Green box, <35% |
| 2. Running | Run across the frame | Yellow→Red box, running flag in log |
| 3. Fight simulation | Two people, rapid arm movements close together | Red boxes, SOS sidebar triggers |
| 4. Weapon | Hold a stick/rod object | Red box, weapon detected in log |

> Frame these as a "controlled demo of 4 threat scenarios" to judges. Do not demo untested situations.

---

## 10. KEY CONSTRAINTS & RULES

- Runs locally only — webcam cannot be streamed through Vercel or any cloud host
- No paid APIs — Gemini free tier is the ONLY external API, used ~5-10 times max in a demo
- Context window rule: paste this file at the top of every new AI chat before asking anything
- One AI owns the full codebase — do not split coding tasks between different AIs
- Use ChatGPT for isolated bug fixes only — Claude handles all architecture and full-file generation
- Always test each file independently before integrating with the next

---

## 11. CURRENT STATUS

- [x] Project vision locked
- [x] Tech stack confirmed  
- [x] Risk scoring logic defined
- [x] UI flow defined
- [x] File structure defined
- [ ] detector.py — NOT STARTED
- [ ] zones.py — NOT STARTED
- [ ] alerts.py — NOT STARTED
- [ ] app.py — NOT STARTED
- [ ] index.html — NOT STARTED
- [ ] dashboard.html — NOT STARTED

**Next step: Build detector.py**

---

*Last updated: Phase 0 complete. Ready for Phase 1.*