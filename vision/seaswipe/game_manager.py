"""
game_manager.py
Handles all two-player game logic:
  - Player assignment (left = P1, right = P2)
  - Distance warnings (< 5 ft → move back, > 7 ft → move closer)
  - Swipe → key press mapping
  - Both-players thumbs-up → Enter key
  - On-screen HUD drawing
"""

import cv2
import math
import pyautogui
from seaswipe.swipe_detector import SwipeManager

# ── Distance thresholds ────────────────────────────────────────────────────
DIST_TOO_CLOSE_FT = 5.0   # ft — warn player to move back
DIST_TOO_FAR_FT   = 7.0   # ft — warn player to move closer

# ── Key mappings ───────────────────────────────────────────────────────────
#   Player 1: left swipe → LEFT arrow,  right swipe → RIGHT arrow
#   Player 2: left swipe → DOWN arrow,  right swipe → UP arrow
PLAYER_KEYS = {
    1: {"left": "left",  "right": "right"},
    2: {"left": "down",  "right": "up"},
}

# ── Thumbs-up: how many consecutive frames both players must hold it ───────
THUMBS_HOLD_FRAMES = 20

# ── Flash display duration ─────────────────────────────────────────────────
FLASH_FRAMES = 35

# ── Colors ─────────────────────────────────────────────────────────────────
COLOR_P1      = (0,  200, 100)   # green-ish
COLOR_P2      = (0,  140, 255)   # blue-ish
COLOR_WARN    = (0,  50,  255)   # red
COLOR_READY   = (0,  230, 230)   # cyan
COLOR_WHITE   = (255, 255, 255)


class PlayerState:
    def __init__(self, number: int):
        self.number       = number
        self.label        = f"Player {number}"
        self.color        = COLOR_P1 if number == 1 else COLOR_P2
        self.swipe_mgr    = SwipeManager(f"P{number}")
        self.flash_pool   = {}    # { direction: frames_remaining }
        self.thumbs_ready = False

    def tick_flash(self):
        self.flash_pool = {k: v - 1 for k, v in self.flash_pool.items() if v > 1}

    def add_flash(self, direction: str):
        self.flash_pool[direction] = FLASH_FRAMES


class GameManager:
    def __init__(self):
        self.players          = [PlayerState(1), PlayerState(2)]
        self._thumbs_counter  = 0   # counts consecutive frames both players thumbs-up

    # ──────────────────────────────────────────────────────────────────────
    def update(self, poses: list, distances: list, thumbs_up_count: int,
               w: int, h: int):
        """
        poses          : list of landmark dicts from PoseTracker (sorted L→R)
        distances      : list of distance floats in ft, parallel to poses
        thumbs_up_count: total thumbs-up hands detected this frame
        w, h           : frame dimensions
        """
        # ── Swipe detection per player ─────────────────────────────────
        for i, player in enumerate(self.players):
            lm = poses[i] if i < len(poses) else None
            player.tick_flash()

            if lm is None:
                player.swipe_mgr.reset_all()
                continue

            events = player.swipe_mgr.update(lm, w, h)
            for direction in events:
                player.add_flash(direction)
                key = PLAYER_KEYS[player.number][direction]
                pyautogui.press(key)
                print(f"[Sea Swipe] {player.label} swiped {direction.upper()} → key '{key}'")

        # ── Thumbs-up ready check (need all 4 hands thumbs-up) ────────
        # 2 players × 2 hands = 4 total thumbs-up required
        if thumbs_up_count >= 4:
            self._thumbs_counter += 1
        else:
            self._thumbs_counter = 0

        if self._thumbs_counter >= THUMBS_HOLD_FRAMES:
            pyautogui.press("enter")
            print("[SlideKick] Both players ready → ENTER")
            self._thumbs_counter = 0   # reset so it doesn't spam

    # ──────────────────────────────────────────────────────────────────────
    def draw(self, frame, poses: list, distances: list, thumbs_up_count: int):
        h, w = frame.shape[:2]

        for i, player in enumerate(self.players):
            lm = poses[i] if i < len(poses) else None

            # ── Player label above their body ──────────────────────────
            if lm is not None:
                sx = int((lm["left_shoulder"][0] + lm["right_shoulder"][0]) / 2 * w)
                sy = int((lm["left_shoulder"][1] + lm["right_shoulder"][1]) / 2 * h) - 30
                self._put_label(frame, player.label, (sx, sy), player.color, scale=0.8, thickness=2)

                # ── Distance warning over their body ───────────────────
                dist = distances[i] if i < len(distances) else None
                if dist is not None:
                    if dist < DIST_TOO_CLOSE_FT:
                        warn = f"{player.label}: Move Back!"
                        self._put_label(frame, warn, (sx, sy + 40), COLOR_WARN, scale=0.75, thickness=2)
                    elif dist > DIST_TOO_FAR_FT:
                        warn = f"{player.label}: Move Closer!"
                        self._put_label(frame, warn, (sx, sy + 40), COLOR_WARN, scale=0.75, thickness=2)

            # ── Swipe flash in corners ──────────────────────────────────
            # P1 → bottom-left,  P2 → bottom-right
            for direction, frames_left in player.flash_pool.items():
                alpha = min(1.0, frames_left / 10)   # fade last 10 frames
                if direction == "left":
                    text = f"<< {player.label} LEFT"
                else:
                    text = f"{player.label} RIGHT >>"

                if player.number == 1:
                    x, y = 20, h - 30
                else:
                    (tw, _), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_DUPLEX, 0.9, 2)
                    x, y = w - tw - 20, h - 30

                cv2.putText(frame, text, (x, y),
                            cv2.FONT_HERSHEY_DUPLEX, 0.9, player.color, 2, cv2.LINE_AA)

        # ── Thumbs-up ready indicator ───────────────────────────────────
        if thumbs_up_count >= 4:
            filled = min(1.0, self._thumbs_counter / THUMBS_HOLD_FRAMES)
            bar_w  = int(200 * filled)
            cx     = w // 2
            cv2.rectangle(frame, (cx - 100, 15), (cx - 100 + bar_w, 40), COLOR_READY, -1)
            cv2.rectangle(frame, (cx - 100, 15), (cx + 100, 40), COLOR_READY, 1)
            self._put_label(frame, "BOTH READY!", (cx - 55, 35), COLOR_READY, scale=0.65)
        elif thumbs_up_count > 0:
            self._put_label(frame, "Waiting for both players...", (w // 2 - 150, 35),
                            COLOR_WHITE, scale=0.6)

    # ──────────────────────────────────────────────────────────────────────
    @staticmethod
    def _put_label(frame, text, pos, color, scale=0.6, thickness=1):
        (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, scale, thickness)
        x, y = pos
        cv2.rectangle(frame, (x - 4, y - th - 6), (x + tw + 4, y + 4), (0, 0, 0), -1)
        cv2.putText(frame, text, (x, y),
                    cv2.FONT_HERSHEY_SIMPLEX, scale, color, thickness, cv2.LINE_AA)
