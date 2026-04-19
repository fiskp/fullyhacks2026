import cv2
import math
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from .download_model import ensure_model

class LandmarkSmoother:
    def __init__(self, alpha=0.3):
        self.alpha = alpha
        self.smoothed_data = {}

    def smooth(self, new_data):
        if not self.smoothed_data:
            self.smoothed_data = new_data
            return new_data
        for key, val in new_data.items():
            prev = self.smoothed_data.get(key, val)
            self.smoothed_data[key] = tuple(
                self.alpha * v + (1 - self.alpha) * p for v, p in zip(val, prev)
            )
        return self.smoothed_data


class PoseTracker:
    """Tracks up to 2 poses. Returns a list of landmark dicts (0, 1, or 2 entries)."""

    def __init__(self):
        model_path = ensure_model()
        base_options = python.BaseOptions(model_asset_path=model_path)
        options = vision.PoseLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.VIDEO,
            output_segmentation_masks=False,
            num_poses=2                          # ← track up to 2 people
        )
        self.landmarker  = vision.PoseLandmarker.create_from_options(options)
        self.frame_idx   = 0
        self.smoothers   = [LandmarkSmoother(alpha=0.3), LandmarkSmoother(alpha=0.3)]

    def norm_to_pixel(self, norm_x, norm_y, frame_width, frame_height):
        return int(norm_x * frame_width), int(norm_y * frame_height)

    def process(self, frame) -> list[dict]:
        """
        Returns list of landmark dicts sorted by shoulder-midpoint X (left → right).
        Index 0 = Player 1 (left side), index 1 = Player 2 (right side).
        Each dict has keys: left_shoulder, right_shoulder, left_elbow, right_elbow,
                            left_wrist, right_wrist
        """
        rgb      = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result   = self.landmarker.detect_for_video(mp_image, self.frame_idx)
        self.frame_idx += 1

        if not result.pose_landmarks:
            return []

        poses = []
        for i, lm in enumerate(result.pose_landmarks):
            raw = {
                "left_shoulder":  (lm[11].x, lm[11].y),
                "right_shoulder": (lm[12].x, lm[12].y),
                "left_elbow":     (lm[13].x, lm[13].y),
                "right_elbow":    (lm[14].x, lm[14].y),
                "left_wrist":     (lm[15].x, lm[15].y),
                "right_wrist":    (lm[16].x, lm[16].y),
            }
            smoother = self.smoothers[i] if i < len(self.smoothers) else LandmarkSmoother()
            poses.append(smoother.smooth(raw))

        # Sort left→right by shoulder midpoint X so index 0 is always Player 1
        poses.sort(key=lambda p: (p["left_shoulder"][0] + p["right_shoulder"][0]) / 2)
        return poses

    def compute_upper_arm_metric(self, landmarks, frame_width):
        def arm_len(s, e):
            dx = s[0] - e[0]; dy = s[1] - e[1]
            return math.sqrt(dx * dx + dy * dy)
        L = arm_len(landmarks["left_shoulder"], landmarks["left_elbow"])
        R = arm_len(landmarks["right_shoulder"], landmarks["right_elbow"])
        return max(L, R) * frame_width


# ── Hand skeleton connections ──────────────────────────────────────────────
HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (0, 9), (9, 10), (10, 11), (11, 12),
    (0, 13), (13, 14), (14, 15), (15, 16),
    (0, 17), (17, 18), (18, 19), (19, 20),
    (5, 9), (9, 13), (13, 17),
]


class HandTracker:
    def __init__(self):
        model_path   = "models/hand_landmarker.task"
        base_options = python.BaseOptions(model_asset_path=model_path)
        options      = vision.HandLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.VIDEO,
            num_hands=4,                         # up to 2 hands per player × 2 players
            min_hand_detection_confidence=0.5,
            min_hand_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self.landmarker = vision.HandLandmarker.create_from_options(options)
        self.frame_idx  = 0

    def process(self, frame) -> list[dict]:
        """Returns list of {pts, handedness} dicts for all detected hands."""
        rgb      = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result   = self.landmarker.detect_for_video(mp_image, self.frame_idx)
        self.frame_idx += 1
        if not result.hand_landmarks:
            return []
        fh, fw = frame.shape[:2]
        hands  = []
        for i, hand in enumerate(result.hand_landmarks):
            pts   = [(int(lm.x * fw), int(lm.y * fh)) for lm in hand]
            label = "Unknown"
            if result.handedness and i < len(result.handedness):
                label = result.handedness[i][0].display_name
            hands.append({"pts": pts, "handedness": label})
        return hands

    def get_thumbs_up_count(self, hands: list) -> int:
        """Returns how many detected hands are showing a thumbs-up."""
        count = 0
        for hand in hands:
            if self._is_thumbs_up(hand["pts"]):
                count += 1
        return count

    @staticmethod
    def _is_thumbs_up(pts) -> bool:
        """
        Thumbs-up: thumb tip (4) is significantly above the wrist (0),
        and all other fingers are curled (tips below their PIP joints).
        """
        wrist_y  = pts[0][1]
        thumb_y  = pts[4][1]
        # Thumb must be clearly above wrist
        if thumb_y >= wrist_y - 20:
            return False
        # Other fingers must be curled: tip Y > PIP Y (lower on screen = higher index)
        for tip, pip in [(8, 6), (12, 10), (16, 14), (20, 18)]:
            if pts[tip][1] < pts[pip][1]:   # finger is extended
                return False
        return True


def draw_hands(frame, hands: list):
    """Draw finger-tracking skeleton and wrist X/Y label for each hand."""
    for hand in hands:
        pts        = hand["pts"]
        handedness = hand["handedness"]
        for start_idx, end_idx in HAND_CONNECTIONS:
            cv2.line(frame, pts[start_idx], pts[end_idx], (0, 220, 255), 2, cv2.LINE_AA)
        for i, pt in enumerate(pts):
            r = 5 if i == 0 else 3
            cv2.circle(frame, pt, r, (255, 255, 255), -1, cv2.LINE_AA)
            cv2.circle(frame, pt, r, (0, 150, 255),   1,  cv2.LINE_AA)
        wx, wy = pts[0]
        label  = f"{handedness}  x:{wx} y:{wy}"
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.52, 1)
        cv2.rectangle(frame, (wx + 8, wy - th - 6), (wx + 8 + tw + 4, wy + 2), (0, 0, 0), -1)
        cv2.putText(frame, label, (wx + 10, wy - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.52, (0, 220, 255), 1, cv2.LINE_AA)


def draw_arm_lines(frame, landmarks: dict, w: int, h: int):
    """Draw elbow→wrist lines and wrist dot + X/Y label using pose landmarks."""
    def to_px(key):
        nx, ny = landmarks[key]
        return int(nx * w), int(ny * h)

    for side, color in [("left", (0, 255, 180)), ("right", (0, 180, 255))]:
        elbow = to_px(f"{side}_elbow")
        wrist = to_px(f"{side}_wrist")
        cv2.line(frame, elbow, wrist, color, 3, cv2.LINE_AA)
        cv2.circle(frame, wrist, 8, (255, 255, 255), -1, cv2.LINE_AA)
        cv2.circle(frame, wrist, 8, color, 2, cv2.LINE_AA)
        wx, wy   = wrist
        label    = f"{side[0].upper()} wrist  x:{wx} y:{wy}"
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        lx = wx + 12 if wx + 12 + tw < w else wx - tw - 12
        cv2.rectangle(frame, (lx - 2, wy - th - 6), (lx + tw + 2, wy + 2), (0, 0, 0), -1)
        cv2.putText(frame, label, (lx, wy - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA)