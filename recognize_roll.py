"""
Roll Number Recognizer
======================
Reads a handwritten roll number written in BLUE INK in the TOP-RIGHT CORNER
of a scanned/photographed exam question paper.

Pipeline:
  1. Load full page image
  2. Crop top-right region (configurable %)
  3. Isolate blue ink using HSV color masking
  4. Find contours → sort digits left-to-right
  5. Feed each digit through the trained CNN
  6. Assemble full roll number string

Usage:
  python recognize_roll.py path/to/paper.jpg
  python recognize_roll.py path/to/paper.jpg --debug   (saves debug images)
"""

import os, sys, argparse
import cv2
import numpy as np
from PIL import Image, ImageFilter
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"
import tensorflow as tf


# ══════════════════════════════════════════════════════════════════════
# CONFIGURATION  — tweak these if results are off
# ══════════════════════════════════════════════════════════════════════

# What fraction of the page to crop as the "roll number zone"
TOP_CROP_FRACTION   = 0.18   # top 18 % of page height
RIGHT_CROP_FRACTION = 0.40   # right 40 % of page width

# HSV range for BLUE INK detection
# Standard blue ballpoint pen falls in this range
BLUE_HSV_LOWER = np.array([90,  50,  50])
BLUE_HSV_UPPER = np.array([135, 255, 255])

# Minimum pixel area for a contour to be considered a digit (noise filter)
MIN_DIGIT_AREA = 80
MAX_DIGIT_AREA = 50_000

MODEL_PATH = "digit_recognizer.keras"


# ══════════════════════════════════════════════════════════════════════
# STEP 1 — CROP TOP-RIGHT CORNER
# ══════════════════════════════════════════════════════════════════════

def crop_top_right(image: np.ndarray, debug=False) -> np.ndarray:
    """Return the top-right region of the full page."""
    h, w = image.shape[:2]
    top    = 0
    bottom = int(h * TOP_CROP_FRACTION)
    left   = int(w * (1 - RIGHT_CROP_FRACTION))
    right  = w

    region = image[top:bottom, left:right]

    if debug:
        cv2.imwrite("debug_1_top_right_crop.jpg", region)
        print(f"[DEBUG] Cropped region: {region.shape} (from {image.shape})")

    return region


# ══════════════════════════════════════════════════════════════════════
# STEP 2 — ISOLATE BLUE INK
# ══════════════════════════════════════════════════════════════════════

def isolate_blue_ink(region: np.ndarray, debug=False) -> np.ndarray:
    """
    Returns a binary mask where blue ink pixels = 255, everything else = 0.
    Works under typical indoor/natural lighting.
    """
    hsv  = cv2.cvtColor(region, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, BLUE_HSV_LOWER, BLUE_HSV_UPPER)

    # Morphological clean-up: close small gaps, remove tiny noise
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))
    mask   = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=1)
    mask   = cv2.morphologyEx(mask, cv2.MORPH_OPEN,  kernel, iterations=1)

    if debug:
        cv2.imwrite("debug_2_blue_mask.jpg", mask)
        print(f"[DEBUG] Blue pixels found: {np.count_nonzero(mask)}")

    return mask


# ══════════════════════════════════════════════════════════════════════
# STEP 3 — FIND & SORT DIGIT CONTOURS
# ══════════════════════════════════════════════════════════════════════

def find_digit_contours(mask: np.ndarray, region: np.ndarray, debug=False):
    """
    Find bounding boxes of individual digits, sorted left→right.
    Returns list of (x, y, w, h) tuples.
    """
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    boxes = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if not (MIN_DIGIT_AREA < area < MAX_DIGIT_AREA):
            continue
        x, y, w, h = cv2.boundingRect(cnt)
        aspect = w / float(h) if h > 0 else 0
        # Filter: digits are taller than wide (or squarish), not thin lines
        if aspect > 2.5:
            continue
        boxes.append((x, y, w, h))

    # Merge boxes that are very close horizontally (parts of same digit)
    boxes = _merge_close_boxes(boxes)

    # Sort left → right
    boxes.sort(key=lambda b: b[0])

    if debug:
        vis = region.copy()
        for i, (x, y, w, h) in enumerate(boxes):
            cv2.rectangle(vis, (x, y), (x+w, y+h), (0, 255, 0), 2)
            cv2.putText(vis, str(i), (x, y-5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,0), 2)
        cv2.imwrite("debug_3_digit_boxes.jpg", vis)
        print(f"[DEBUG] Digits found: {len(boxes)}")

    return boxes


def _merge_close_boxes(boxes, gap_threshold=3):
    """Merge horizontally adjacent bounding boxes (e.g. dot + body of 'i'-like strokes)."""
    if not boxes:
        return boxes
    boxes = sorted(boxes, key=lambda b: b[0])
    merged = [boxes[0]]
    for x, y, w, h in boxes[1:]:
        px, py, pw, ph = merged[-1]
        if x - (px + pw) < gap_threshold:          # close enough → merge
            nx = min(px, x)
            ny = min(py, y)
            nw = max(px+pw, x+w) - nx
            nh = max(py+ph, y+h) - ny
            merged[-1] = (nx, ny, nw, nh)
        else:
            merged.append((x, y, w, h))
    return merged


# ══════════════════════════════════════════════════════════════════════
# STEP 4 — PREPROCESS EACH DIGIT FOR THE CNN
# ══════════════════════════════════════════════════════════════════════

def preprocess_digit(mask: np.ndarray, box) -> np.ndarray:
    """
    Crop one digit from the blue-ink mask, resize to 28×28 MNIST style.
    Returns shape (1, 28, 28, 1) float32.
    """
    x, y, w, h = box
    pad = 6
    x1 = max(0, x - pad);  y1 = max(0, y - pad)
    x2 = min(mask.shape[1], x + w + pad)
    y2 = min(mask.shape[0], y + h + pad)

    digit_mask = mask[y1:y2, x1:x2]

    # PIL for better resizing
    pil = Image.fromarray(digit_mask)
    pil.thumbnail((20, 20), Image.LANCZOS)

    canvas = Image.new("L", (28, 28), 0)
    xo = (28 - pil.width)  // 2
    yo = (28 - pil.height) // 2
    canvas.paste(pil, (xo, yo))
    canvas = canvas.filter(ImageFilter.GaussianBlur(0.5))

    arr = np.array(canvas, dtype="float32") / 255.0
    return arr.reshape(1, 28, 28, 1)


# ══════════════════════════════════════════════════════════════════════
# STEP 5 — RECOGNISE ALL DIGITS → ASSEMBLE ROLL NUMBER
# ══════════════════════════════════════════════════════════════════════

def recognise_roll_number(image_path: str, debug: bool = False) -> str:
    # Load model
    if not os.path.exists(MODEL_PATH):
        print(f"ERROR: Model not found at '{MODEL_PATH}'")
        print("Please run  train_model.py  first.")
        sys.exit(1)
    model = tf.keras.models.load_model(MODEL_PATH)

    # Load image
    image = cv2.imread(image_path)
    if image is None:
        print(f"ERROR: Cannot read image at '{image_path}'")
        sys.exit(1)
    print(f"Image loaded: {image.shape[1]}×{image.shape[0]} px")

    # Pipeline
    region = crop_top_right(image, debug)
    mask   = isolate_blue_ink(region, debug)
    boxes  = find_digit_contours(mask, region, debug)

    if not boxes:
        print("\n⚠  No blue handwritten digits detected in top-right corner.")
        print("   Tips:")
        print("   • Make sure the roll number is written in BLUE ink")
        print("   • Try --debug flag to inspect intermediate images")
        print("   • Adjust TOP_CROP_FRACTION / RIGHT_CROP_FRACTION in this file")
        return "NOT FOUND"

    roll_number = ""
    print(f"\nDetected {len(boxes)} digit(s):")
    print("─" * 40)

    for i, box in enumerate(boxes):
        arr   = preprocess_digit(mask, box)
        probs = model.predict(arr, verbose=0)[0]
        digit = int(np.argmax(probs))
        conf  = float(probs[digit]) * 100
        roll_number += str(digit)
        print(f"  Digit {i+1}: {digit}  (confidence: {conf:.1f}%)")

    print("─" * 40)
    print(f"\n  ✅  Roll Number: {roll_number}")
    return roll_number


# ══════════════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Recognise roll number from exam paper")
    parser.add_argument("image", help="Path to exam paper image (jpg/png)")
    parser.add_argument("--debug", action="store_true",
                        help="Save intermediate debug images to current folder")
    args = parser.parse_args()

    result = recognise_roll_number(args.image, debug=args.debug)

    # Save result to text file
    out_file = "roll_number_result.txt"
    with open(out_file, "w") as f:
        image_name = os.path.basename(args.image)
        f.write(f"Image     : {image_name}\n")
        f.write(f"Roll No.  : {result}\n")
    print(f"\nResult saved → {out_file}")
