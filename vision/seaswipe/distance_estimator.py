from .config import CALIBRATION_SHOULDER_M

def estimate_distance_ft(arm_px, f_px, arm_real_m=CALIBRATION_SHOULDER_M):
    Z_m = (f_px * arm_real_m) / arm_px
    Z_ft = Z_m * 3.28084

    feet = int(Z_ft)
    inches = int((Z_ft - feet) * 12)

    return Z_ft, feet, inches
