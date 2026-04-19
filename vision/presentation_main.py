import cv2
from seaswipe.camera_manager import CameraManager
from seaswipe.pose_tracker import PoseTracker, HandTracker, draw_hands, draw_arm_lines
from seaswipe.overlay import draw_skeleton
from seaswipe.presentation_manager import PresentationManager

def main():
    # ── Initialization ─────────────────────────────────────────────────────
    cam          = CameraManager(0)
    pose_tracker = PoseTracker()
    hand_tracker = HandTracker()
    pres_manager = PresentationManager()
    
    print("[SlideKick] Presentation Mode Active.")
    print("Controls: Swipe LEFT for Previous, Swipe RIGHT for Next.")
    print("Action: Both players Thumbs-Up to trigger ENTER.")

    while True:
        frame = cam.read()
        if frame is None:
            break
            
        # Mirror the frame so that moving your physical right hand 
        # moves the hand on the right side of the screen.
        frame = cv2.flip(frame, 1)
        h, w  = frame.shape[:2]

        # ── 1. Pose Detection (Up to 2 Presenters) ─────────────────────────
        # Returns a list of landmarks sorted left-to-right
        poses = pose_tracker.process(frame)

        # ── 2. Visual Feedback (Skeletons & Arms) ──────────────────────────
        for lm in poses:
            draw_skeleton(frame, lm, w, h, pose_tracker)
            draw_arm_lines(frame, lm, w, h)

        # ── 3. Hand Tracking (For Thumbs-Up Detection) ─────────────────────
        hands = hand_tracker.process(frame)
        thumbs_up_total = hand_tracker.get_thumbs_up_count(hands)
        
        if hands:
            draw_hands(frame, hands)

        # ── 4. Presentation Logic ──────────────────────────────────────────
        # Process swipes and "Ready" state for both users
        pres_manager.update(poses, thumbs_up_total, w, h)
        pres_manager.draw_hud(frame, thumbs_up_total)

        # ── 5. Display ─────────────────────────────────────────────────────
        cv2.imshow("SlideKick - Presentation Vision", frame)

        # Press 'q' to exit the loop
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # ── Cleanup ────────────────────────────────────────────────────────────
    cam.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()