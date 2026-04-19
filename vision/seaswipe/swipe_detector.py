import cv2
import math

# ── Tuning constants ───────────────────────────────────────────────────────
SPEED_THRESHOLD = 40   # px/frame  — min wrist speed to start a burst
DIST_THRESHOLD  = 80   # px        — min net X travel to fire a swipe
PEAK_SPEED_MIN  = 35   # px/frame  — peak speed needed to confirm intent
COOLDOWN_FRAMES = 10   # frames    — lock-out after a swipe fires
ARM_ANGLE_MAX   = 150  # degrees   — elbow→wrist angle limit
TORSO_MOVE_MAX  = 60   # px        — max shoulder-midpoint drift during burst
Y_BAND_PX       = 100   # px        — wrist must stay within ±40px of swipe-start Y;
                        #             crossing this band IMMEDIATELY cancels the burst


class HandSwipeDetector:
    """Velocity-burst swipe detector for one arm side of one player."""

    def __init__(self, label: str):
        self.label        = label
        self._prev_x      = None
        self._in_burst    = False
        self._origin_x    = None
        self._origin_y    = None   # Y locked when burst starts — centre of the band
        self._peak_speed  = 0.0
        self._cooldown    = 0

    def update_xy(self, wrist_x: int, wrist_y: int = 0) -> str | None:
        if self._cooldown > 0:
            self._cooldown -= 1

        if self._prev_x is None:
            self._prev_x = wrist_x
            return None

        velocity     = wrist_x - self._prev_x
        speed        = abs(velocity)
        self._prev_x = wrist_x
        event        = None

        if not self._in_burst:
            if speed >= SPEED_THRESHOLD:
                self._in_burst   = True
                self._origin_x   = wrist_x
                self._origin_y   = wrist_y   # lock Y band centre here
                self._peak_speed = speed
        else:
            # ── Y band gate — cancel burst immediately if wrist leaves band ──
            if abs(wrist_y - self._origin_y) > Y_BAND_PX:
                print(f"[SlideKick] {self.label} CANCELLED — left Y band "
                      f"(drift {abs(wrist_y - self._origin_y)}px)")
                self._in_burst   = False
                self._origin_x   = None
                self._origin_y   = None
                self._peak_speed = 0.0
                return None

            if speed > self._peak_speed:
                self._peak_speed = speed

            if speed < SPEED_THRESHOLD:
                net_x = wrist_x - self._origin_x
                if (abs(net_x) >= DIST_THRESHOLD
                        and self._peak_speed >= PEAK_SPEED_MIN
                        and self._cooldown == 0):
                    event          = "right" if net_x > 0 else "left"
                    self._cooldown = COOLDOWN_FRAMES
                self._in_burst   = False
                self._origin_x   = None
                self._origin_y   = None
                self._peak_speed = 0.0

        return event

    def reset(self):
        self._prev_x     = None
        self._in_burst   = False
        self._origin_x   = None
        self._origin_y   = None
        self._peak_speed = 0.0
        self._cooldown   = 0


class SwipeManager:
    """
    Per-player swipe manager. One instance per player.
    Tracks both arm sides, applies arm-angle + torso-stability gates.
    Y-band gate is handled inside HandSwipeDetector itself.
    """

    SIDE_MAP = {
        "Left":  ("left_elbow",  "left_wrist"),
        "Right": ("right_elbow", "right_wrist"),
    }

    def __init__(self, player_label: str):
        self.player_label  = player_label
        self._detectors    = {
            "Left":  HandSwipeDetector(f"{player_label}-Left"),
            "Right": HandSwipeDetector(f"{player_label}-Right"),
        }
        self._torso_origin = {"Left": None, "Right": None}

    @staticmethod
    def _arm_angle_deg(elbow_px, wrist_px) -> float:
        dx = wrist_px[0] - elbow_px[0]
        dy = wrist_px[1] - elbow_px[1]
        return math.degrees(math.atan2(abs(dy), abs(dx)))

    @staticmethod
    def _shoulder_mid(landmarks, w, h) -> tuple:
        lsx, lsy = landmarks["left_shoulder"]
        rsx, rsy = landmarks["right_shoulder"]
        return (int((lsx + rsx) / 2 * w), int((lsy + rsy) / 2 * h))

    def update(self, landmarks: dict, w: int, h: int) -> list[str]:
        """Returns list of direction strings ('left'/'right') that fired this frame."""
        events = []

        if landmarks is None:
            for det in self._detectors.values():
                det.reset()
            self._torso_origin = {"Left": None, "Right": None}
            return events

        shoulder_mid = self._shoulder_mid(landmarks, w, h)

        for side, (elbow_key, wrist_key) in self.SIDE_MAP.items():
            det = self._detectors[side]

            ex, ey   = landmarks[elbow_key]
            wx, wy   = landmarks[wrist_key]
            elbow_px = (int(ex * w), int(ey * h))
            wrist_px = (int(wx * w), int(wy * h))
            wrist_x  = wrist_px[0]
            wrist_y  = wrist_px[1]

            # Gate 1: arm angle
            if self._arm_angle_deg(elbow_px, wrist_px) > ARM_ANGLE_MAX:
                det.reset()
                self._torso_origin[side] = None
                continue

            # Capture burst start for torso check
            was_in_burst = det._in_burst
            result       = det.update_xy(wrist_x, wrist_y)
            if det._in_burst and not was_in_burst:
                self._torso_origin[side] = shoulder_mid

            # Gate 2: torso stability
            if result is not None and self._torso_origin[side] is not None:
                ox, oy = self._torso_origin[side]
                cx, cy = shoulder_mid
                drift  = math.sqrt((cx - ox) ** 2 + (cy - oy) ** 2)
                if drift > TORSO_MOVE_MAX:
                    print(f"[SlideKick] {self.player_label} {side} BLOCKED — torso {drift:.1f}px")
                    result = None
                self._torso_origin[side] = None

            if result:
                events.append(result)

        return events

    def reset_all(self):
        for det in self._detectors.values():
            det.reset()
        self._torso_origin = {"Left": None, "Right": None}