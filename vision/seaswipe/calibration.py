import math
from .config import CALIBRATION_DISTANCE_FT, CALIBRATION_SHOULDER_M

class CalibrationState:
    def __init__(self):
        self.f_px = None
        self.samples = []

    def add_sample(self, corrected_shoulder_px):
        self.samples.append(corrected_shoulder_px)

    def is_ready(self, min_samples=30):
        return len(self.samples) >= min_samples

    def compute_focal_length(self):
        if not self.samples:
            return None
        Z_m = CALIBRATION_DISTANCE_FT * 0.3048
        W_real = CALIBRATION_SHOULDER_M
        median_px = sorted(self.samples)[len(self.samples)//2]
        self.f_px = (median_px * Z_m) / W_real
        return self.f_px
