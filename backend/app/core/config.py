import os

UPLOAD_DIR = os.path.abspath("uploads")
OUTPUT_DIR = os.path.abspath("output")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)