from collections import deque
import numpy as np
from .config import SMOOTHING_WINDOW

class RollingSmoother:
    def __init__(self, window=SMOOTHING_WINDOW):
        self.values = deque(maxlen=window)

    def add(self, v):
        self.values.append(v)
        return self.get()

    def get(self):
        if not self.values:
            return None
        return float(np.median(self.values))


class EMASmoother:
    def __init__(self, alpha=0.35):
        self.alpha = alpha
        self.value = None

    def add(self, v):
        if v is None:
            return self.value
        if self.value is None:
            self.value = v
        else:
            self.value = self.alpha * v + (1 - self.alpha) * self.value
        return self.value
