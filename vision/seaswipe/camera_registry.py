import json
import os

REGISTRY_DIR = "camera_profiles"

def ensure_registry_dir():
    if not os.path.isdir(REGISTRY_DIR):
        os.makedirs(REGISTRY_DIR)

def get_camera_profile_path(camera_id):
    ensure_registry_dir()
    filename = f"{camera_id}.json"
    return os.path.join(REGISTRY_DIR, filename)

def load_camera_profile(camera_id):
    path = get_camera_profile_path(camera_id)
    if not os.path.isfile(path):
        return None
    with open(path, "r") as f:
        return json.load(f)

def save_camera_profile(camera_id, data):
    path = get_camera_profile_path(camera_id)
    with open(path, "w") as f:
        json.dump(data, f, indent=4)

def get_camera_id(cap):
    backend = cap.getBackendName()
    w = int(cap.get(3))
    h = int(cap.get(4))
    return f"{backend}_{w}x{h}"
