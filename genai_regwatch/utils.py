import os

def compute_hash(file_content):
    import hashlib
    return hashlib.sha256(file_content).hexdigest()

# ---------------------------- Updated ----------------------------
def save_file_locally(file_content, filename):
    from .config import LOCAL_STORAGE
    os.makedirs(LOCAL_STORAGE, exist_ok=True)
    path = os.path.join(LOCAL_STORAGE, filename)
    with open(path, "wb") as f:
        f.write(file_content)
    return path

def read_file(file_path):
    with open(file_path, "rb") as f:
        return f.read()
