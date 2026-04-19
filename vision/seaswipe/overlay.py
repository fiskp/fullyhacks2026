import cv2

def draw_overlay(frame, distance_ft, feet, inches, f_px, calibrated, camera_id, auto_loaded):
    y = 30
    color = (0, 255, 0)
    scale = 0.7

    def put(text):
        nonlocal y
        cv2.putText(frame, text, (10, y), cv2.FONT_HERSHEY_SIMPLEX, scale, color, 2)
        y += 30

    if auto_loaded:
        put(f"Camera: {camera_id} (auto-loaded)")
    else:
        put(f"Camera: {camera_id} (new)")

    if calibrated:
        put(f"Distance: {feet} ft {inches} in ({distance_ft:.2f} ft)")
        put(f"f_px: {f_px:.1f}")
    else:
        put("CALIBRATION MODE: Stand at 2 ft")
        put("Press SPACEBAR to calibrate")

def draw_skeleton(frame, landmarks, w, h, pose_tracker):
    # Only tracking shoulders and elbows as requested
    parts = [
        ("left_shoulder", "right_shoulder"),
        ("left_shoulder", "left_elbow"),
        ("right_shoulder", "right_elbow")
    ]
    for start, end in parts:
        pt1 = pose_tracker.norm_to_pixel(landmarks[start][0], landmarks[start][1], w, h)
        pt2 = pose_tracker.norm_to_pixel(landmarks[end][0], landmarks[end][1], w, h)
        cv2.line(frame, pt1, pt2, (0, 255, 0), 3)
        cv2.circle(frame, pt1, 6, (0, 0, 255), -1)
        cv2.circle(frame, pt2, 6, (0, 0, 255), -1)

# Note: draw_vertical_boundaries is no longer used since you 
# removed swipe/boundary detection, but you can leave it 
# empty or delete it to keep your code clean.