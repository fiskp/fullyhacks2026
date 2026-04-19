import os
import urllib.request

MODEL_URL = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/latest/pose_landmarker_full.task"
MODEL_PATH = os.path.join("models", "pose_landmarker_full.task")

def ensure_model():
    if not os.path.exists("models"):
        os.makedirs("models")

    if not os.path.isfile(MODEL_PATH):
        print("Downloading pose_landmarker_full.task...")
        urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
        print("Download complete.")
    else:
        print("Model already exists.")

    return MODEL_PATH
