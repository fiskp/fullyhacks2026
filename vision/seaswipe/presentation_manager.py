"""
presentation_manager.py
Handles presentation logic:
  - Swipe left  -> Right arrow (Next Slide)
  - Swipe right -> Left arrow (Previous Slide)
  - Both-players thumbs-up -> Enter (Start/Reset Presentation)
"""

import cv2
import pyautogui
from seaswipe.swipe_detector import SwipeManager

# Configuration
THUMBS_HOLD_FRAMES = 20
COLOR_READY = (0, 230, 230)
COLOR_TEXT  = (255, 255, 255)

class PresentationManager:
    def __init__(self):
        # Track up to 2 people
        self.swipers = [SwipeManager("P1"), SwipeManager("P2")]
        self._thumbs_counter = 0

    def update(self, poses, thumbs_up_count, w, h):
        # 1. Process Swipes for both people
        for i, swiper in enumerate(self.swipers):
            lm = poses[i] if i < len(poses) else None
            
            if lm is None:
                swiper.reset_all()
                continue

            events = swiper.update(lm, w, h)
            for direction in events:
                if direction == "left":
                    # Swiping left moves to the NEXT slide
                    pyautogui.press("right")
                    print("[SlideKick] Swipe LEFT -> Next Slide (Right Arrow)")
                elif direction == "right":
                    # Swiping right moves to the PREVIOUS slide
                    pyautogui.press("left")
                    print("[SlideKick] Swipe RIGHT -> Previous Slide (Left Arrow)")

        # 2. Process "Ready" (Thumbs Up)
        # Requires 4 hands total (2 people) to be showing thumbs up
        if thumbs_up_count >= 4:
            self._thumbs_counter += 1
        else:
            self._thumbs_counter = 0

        if self._thumbs_counter >= THUMBS_HOLD_FRAMES:
            pyautogui.press("enter")
            print("[SlideKick] Both players ready -> ENTER")
            self._thumbs_counter = 0

    def draw_hud(self, frame, thumbs_up_count):
        h, w = frame.shape[:2]
        
        if thumbs_up_count >= 4:
            filled = min(1.0, self._thumbs_counter / THUMBS_HOLD_FRAMES)
            bar_w = int(200 * filled)
            cx = w // 2
            cv2.rectangle(frame, (cx - 100, 15), (cx - 100 + bar_w, 40), COLOR_READY, -1)
            cv2.rectangle(frame, (cx - 100, 15), (cx + 100, 40), COLOR_READY, 1)
            cv2.putText(frame, "READY", (cx - 30, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.6, COLOR_READY, 2)
        elif 0 < thumbs_up_count < 4:
            cv2.putText(frame, "Waiting for both presenters...", (w // 2 - 120, 30), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, COLOR_TEXT, 1)