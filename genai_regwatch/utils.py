import os
import hashlib

def compute_hash(file_content):
    return hashlib.sha256(file_content).hexdigest()

def save_file_locally(file_content, filename):
    from .config import LOCAL_STORAGE
    os.makedirs(LOCAL_STORAGE, exist_ok=True)

    # Always resolve to absolute path
    path = os.path.abspath(os.path.join(LOCAL_STORAGE, filename))
    with open(path, "wb") as f:
        f.write(file_content)

    return path   # absolute path saved in DB

def read_file(file_path):
    # Normalize path in case DB stored forward slashes
    path = os.path.abspath(file_path)

    if not os.path.exists(path):
        raise FileNotFoundError(f"[ERROR] File not found: {path}")

    with open(path, "rb") as f:
        return f.read()

