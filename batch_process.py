"""
batch_process.py — Process a FOLDER of exam papers and export results to CSV

Usage:
    python batch_process.py path/to/folder/
    python batch_process.py path/to/folder/ --debug
"""

import os, sys, argparse, csv
from datetime import datetime
import cv2
import numpy as np
from PIL import Image, ImageFilter
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"
import tensorflow as tf

# Reuse the core pipeline from recognize_roll.py
sys.path.insert(0, os.path.dirname(__file__))
from recognize_roll import (
    crop_top_right, isolate_blue_ink,
    find_digit_contours, preprocess_digit,
    MODEL_PATH
)

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif"}


def process_folder(folder_path: str, debug: bool = False):
    # ── Validate folder ────────────────────────────────────────────────
    if not os.path.isdir(folder_path):
        print(f"ERROR: '{folder_path}' is not a valid folder.")
        sys.exit(1)

    # ── Load model once ────────────────────────────────────────────────
    if not os.path.exists(MODEL_PATH):
        print(f"ERROR: Model not found. Run train_model.py first.")
        sys.exit(1)

    print("Loading CNN model … ", end="", flush=True)
    model = tf.keras.models.load_model(MODEL_PATH)
    print("done.\n")

    # ── Gather image files ─────────────────────────────────────────────
    image_files = sorted([
        f for f in os.listdir(folder_path)
        if os.path.splitext(f)[1].lower() in SUPPORTED_EXTENSIONS
    ])

    if not image_files:
        print(f"No image files found in '{folder_path}'")
        sys.exit(1)

    print(f"Found {len(image_files)} image(s) to process.\n")
    print(f"{'File':<35} {'Roll Number':<20} {'Digits':<8} {'Status'}")
    print("─" * 75)

    results = []

    for fname in image_files:
        fpath  = os.path.join(folder_path, fname)
        image  = cv2.imread(fpath)

        if image is None:
            print(f"{fname:<35} {'—':<20} {'—':<8} ❌ Cannot read")
            results.append({"file": fname, "roll_number": "ERROR", "digit_count": 0})
            continue

        try:
            region = crop_top_right(image, debug=False)
            mask   = isolate_blue_ink(region, debug=False)
            boxes  = find_digit_contours(mask, region, debug=False)

            if not boxes:
                print(f"{fname:<35} {'NOT FOUND':<20} {'0':<8} ⚠  No digits detected")
                results.append({"file": fname, "roll_number": "NOT FOUND", "digit_count": 0})
                continue

            roll = ""
            for box in boxes:
                arr   = preprocess_digit(mask, box)
                probs = model.predict(arr, verbose=0)[0]
                roll += str(int(np.argmax(probs)))

            print(f"{fname:<35} {roll:<20} {len(boxes):<8} ✅")
            results.append({"file": fname, "roll_number": roll, "digit_count": len(boxes)})

        except Exception as e:
            print(f"{fname:<35} {'ERROR':<20} {'—':<8} ❌ {e}")
            results.append({"file": fname, "roll_number": f"ERROR: {e}", "digit_count": 0})

    # ── Save CSV ───────────────────────────────────────────────────────
    timestamp  = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path   = f"roll_numbers_{timestamp}.csv"

    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["file", "roll_number", "digit_count"])
        writer.writeheader()
        writer.writerows(results)

    success = sum(1 for r in results if r["roll_number"] not in ("NOT FOUND", "ERROR") and not r["roll_number"].startswith("ERROR"))
    print("─" * 75)
    print(f"\n✅  Processed {success}/{len(image_files)} papers successfully")
    print(f"📄  Results saved → {csv_path}")
    return csv_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Batch process exam papers")
    parser.add_argument("folder", help="Folder containing exam paper images")
    parser.add_argument("--debug", action="store_true", help="Save debug images")
    args = parser.parse_args()
    process_folder(args.folder, debug=args.debug)
