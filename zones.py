import cv2
import numpy as np # <--- CRITICAL FIX: Add this

ZONES = {
    "Entrance": {
        "x": 50, 
        "y": 50, 
        "w": 120, 
        "h": 120, 
        "color": (255, 255, 0)
    },
    "Secure-X": {
        "x": 470, 
        "y": 310, 
        "w": 120, 
        "h": 120, 
        "color": (0, 165, 255)
    }
}

def get_zone_for_bbox(x1, y1, x2, y2):
    cx = (x1 + x2) / 2
    cy = (y1 + y2) / 2
    for name, z in ZONES.items():
        if (z["x"] <= cx <= z["x"] + z["w"]) and (z["y"] <= cy <= z["y"] + z["h"]):
            return name
    return "Neutral"

def draw_zones(frame):
    h_max, w_max = frame.shape[:2]
    for name, z in ZONES.items():
        # Ensure coordinates are within frame limits to prevent slicing errors
        x, y = max(0, z["x"]), max(0, z["y"])
        w, h = min(z["w"], w_max - x), min(z["h"], h_max - y)
        
        # Draw semi-transparent square
        sub_face = frame[y:y+h, x:x+w]
        if sub_face.size > 0:
            color_rect = np.full(sub_face.shape, z["color"], dtype=np.uint8)
            res = cv2.addWeighted(sub_face, 0.9, color_rect, 0.1, 0)
            frame[y:y+h, x:x+w] = res

        # Draw borders and labels
        cv2.rectangle(frame, (x, y), (x + w, y + h), z["color"], 1)
        cv2.putText(frame, name, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, z["color"], 1)
    return frame