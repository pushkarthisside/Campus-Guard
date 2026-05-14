import cv2

# ─────────────────────────────────────────────────────────────────────────────
# CAMERA ZONES
# ─────────────────────────────────────────────────────────────────────────────

ZONES = {
    "Gate": {
        "x1": 0,
        "y1": 0,
        "x2": 213,
        "y2": 480,
        "color": (255, 255, 0)
    },

    "Corridor": {
        "x1": 213,
        "y1": 0,
        "x2": 426,
        "y2": 480,
        "color": (0, 255, 255)
    },

    "Lab": {
        "x1": 426,
        "y1": 0,
        "x2": 640,
        "y2": 480,
        "color": (255, 165, 0)
    }
}

# ─────────────────────────────────────────────────────────────────────────────
# GET ZONE FOR PERSON
# ─────────────────────────────────────────────────────────────────────────────

def get_zone_for_bbox(x1, y1, x2, y2):

    cx = (x1 + x2) / 2
    cy = (y1 + y2) / 2

    for zone_name, zone in ZONES.items():

        if (
            zone["x1"] <= cx <= zone["x2"] and
            zone["y1"] <= cy <= zone["y2"]
        ):
            return zone_name

    return "Unknown"

# ─────────────────────────────────────────────────────────────────────────────
# DRAW ZONES
# ─────────────────────────────────────────────────────────────────────────────

def draw_zones(frame):

    overlay = frame.copy()

    for zone_name, zone in ZONES.items():

        # Transparent fill
        cv2.rectangle(
            overlay,
            (zone["x1"], zone["y1"]),
            (zone["x2"], zone["y2"]),
            zone["color"],
            -1
        )

    # Blend overlay
    cv2.addWeighted(
        overlay,
        0.08,
        frame,
        0.92,
        0,
        frame
    )

    # Borders + Labels
    for zone_name, zone in ZONES.items():

        cv2.rectangle(
            frame,
            (zone["x1"], zone["y1"]),
            (zone["x2"], zone["y2"]),
            zone["color"],
            1
        )

        cv2.putText(
            frame,
            zone_name,
            (zone["x1"] + 8, zone["y1"] + 22),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            zone["color"],
            2
        )

    return frame