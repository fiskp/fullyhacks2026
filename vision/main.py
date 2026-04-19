import cv2
from seaswipe.camera_manager import CameraManager
from seaswipe.pose_tracker import PoseTracker, HandTracker, draw_hands, draw_arm_lines
from seaswipe.calibration import CalibrationState
from seaswipe.distance_estimator import estimate_distance_ft
from seaswipe.smoothing import EMASmoother
from seaswipe.overlay import draw_overlay, draw_skeleton
from seaswipe.camera_registry import load_camera_profile, get_camera_id
from seaswipe.game_manager import GameManager

def main():
    cam          = CameraManager(0)
    pose_tracker = PoseTracker()
    hand_tracker = HandTracker()
    game         = GameManager()
    calib        = CalibrationState()
    cam_id       = get_camera_id(cam.cap)
    calibrated   = False

    # One distance smoother per player slot
    smoothers  = [CalibrationState(), CalibrationState()]
    dist_smooth = [__import__('seaswipe.smoothing', fromlist=['EMASmoother']).EMASmoother(0.35),
                   __import__('seaswipe.smoothing', fromlist=['EMASmoother']).EMASmoother(0.35)]

    profile = load_camera_profile(cam_id)
    f_px    = profile["f_px"] if profile else None

    while True:
        frame = cam.read()
        frame = cv2.flip(frame, 1)          # mirror so left/right feel natural
        h, w  = frame.shape[:2]

        # ── Pose detection (up to 2 players) ──────────────────────────
        poses = pose_tracker.process(frame)

        # ── Distance estimation per player ─────────────────────────────
        distances = []
        for i, lm in enumerate(poses):
            arm_px = pose_tracker.compute_upper_arm_metric(lm, w)
            if not f_px:
                calib = smoothers[i]
                calib.add_sample(arm_px)
                f_px_use = calib.f_px
            else:
                f_px_use = f_px
            if f_px_use:
                d, _, _ = estimate_distance_ft(arm_px, f_px_use)
                distances.append(dist_smooth[i].add(d))
            else:
                distances.append(None)

        # ── Draw skeleton + arm lines per player ───────────────────────
        for lm in poses:
            draw_skeleton(frame, lm, w, h, pose_tracker)
            draw_arm_lines(frame, lm, w, h)

        # ── Hand tracking (finger skeleton, thumbs-up detection) ───────
        hands          = hand_tracker.process(frame)
        thumbs_up_total = hand_tracker.get_thumbs_up_count(hands)
        if hands:
            draw_hands(frame, hands)

        # ── Game logic (swipes, keys, distance warnings, HUD) ──────────
        game.update(poses, distances, thumbs_up_total, w, h)
        game.draw(frame, poses, distances, thumbs_up_total)

        # ── Legacy single-player distance overlay (first player only) ──
        if poses and distances and distances[0] is not None and f_px:
            arm_px   = pose_tracker.compute_upper_arm_metric(poses[0], w)
            d, f, i_ = estimate_distance_ft(arm_px, f_px)
            draw_overlay(frame, distances[0], f, i_, f_px, bool(profile), cam_id, True)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
        cv2.imshow("Sea Swipe Vision", frame)

    cam.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()