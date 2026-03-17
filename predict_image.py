"""
predict_image.py — Predict ALL digits in a handwritten image

Detects every digit individually using connected-component analysis,
predicts each one, and saves an annotated result image.

Usage:
    python predict_image.py my_numbers.png
"""

import sys
import os
import numpy as np
from PIL import Image, ImageFilter

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"
import tensorflow as tf
import cv2

MODEL_PATH = "models/digit_recognizer.keras"

# ═══════════════════════════════════════════════════════════════════════════
# 1. SEGMENTATION — find each digit's bounding box
# ═══════════════════════════════════════════════════════════════════════════

def segment_digits(image_path: str):
    """
    Returns a list of (x, y, w, h) bounding boxes for each digit found,
    sorted left-to-right / top-to-bottom.
    Also returns the pre-processed grayscale array and original BGR image.
    """
    img_bgr = cv2.imread(image_path)
    if img_bgr is None:
        raise FileNotFoundError(f"Cannot open '{image_path}'")
    
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    
    # Auto-invert: need WHITE digits on BLACK background
    if gray.mean() > 127:
        gray = cv2.bitwise_not(gray)
    
    # Threshold → binary
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # Mild dilation to connect broken strokes within ONE digit
    kernel  = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    dilated = cv2.dilate(binary, kernel, iterations=2)
    
    # Connected components
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(dilated, connectivity=8)
    
    img_h, img_w = binary.shape
    min_area = img_w * img_h * 0.001   # ignore specks < 0.1% of image
    
    boxes = []
    for i in range(1, num_labels):     # 0 = background
        x    = stats[i, cv2.CC_STAT_LEFT]
        y    = stats[i, cv2.CC_STAT_TOP]
        w    = stats[i, cv2.CC_STAT_WIDTH]
        h    = stats[i, cv2.CC_STAT_HEIGHT]
        area = stats[i, cv2.CC_STAT_AREA]
        
        if area >= min_area:
            boxes.append((x, y, w, h))
    
    # Merge boxes that are very close (e.g. "i" dot + stem, or ":" colon parts)
    boxes = _merge_nearby_boxes(boxes, gap=15)
    
    # Sort: left→right within each row, rows top→bottom
    boxes.sort(key=lambda b: (b[1] // 60, b[0]))
    
    return boxes, gray, img_bgr

def _merge_nearby_boxes(boxes, gap=15):
    """Merge horizontally close boxes that also overlap vertically."""
    if not boxes:
        return boxes
    
    boxes = sorted(boxes, key=lambda b: b[0])
    merged = [list(boxes[0])]
    
    for x, y, w, h in boxes[1:]:
        px, py, pw, ph = merged[-1]
        
        horiz_close = x <= px + pw + gap
        vert_overlap = not (y > py + ph or y + h < py)
        
        if horiz_close and vert_overlap:
            nx = min(px, x);  ny = min(py, y)
            nw = max(px + pw, x + w) - nx
            nh = max(py + ph, y + h) - ny
            merged[-1] = [nx, ny, nw, nh]
        else:
            merged.append([x, y, w, h])
    
    return [tuple(b) for b in merged]

# ═══════════════════════════════════════════════════════════════════════════
# 2. PRE-PROCESS a single cropped digit → 28×28 array
# ═══════════════════════════════════════════════════════════════════════════

def preprocess_digit(gray: np.ndarray, box) -> np.ndarray:
    """Crop box from gray image, resize to MNIST style, return (1,28,28,1)."""
    x, y, w, h = box
    
    margin = max(4, int(min(w, h) * 0.15))
    ih, iw = gray.shape
    
    x1, y1 = max(0, x - margin), max(0, y - margin)
    x2, y2 = min(iw, x + w + margin), min(ih, y + h + margin)
    
    crop = gray[y1:y2, x1:x2]
    
    pil  = Image.fromarray(crop)
    pil.thumbnail((20, 20), Image.LANCZOS)
    
    canvas = Image.new("L", (28, 28), 0)
    xo = (28 - pil.width)  // 2
    yo = (28 - pil.height) // 2
    canvas.paste(pil, (xo, yo))
    
    canvas = canvas.filter(ImageFilter.GaussianBlur(0.5))
    arr = np.array(canvas, dtype="float32") / 255.0
    
    return arr.reshape(1, 28, 28, 1)

# ═══════════════════════════════════════════════════════════════════════════
# 3. ANNOTATE & SAVE result image
# ═══════════════════════════════════════════════════════════════════════════

def save_annotated(image_path, img_bgr, boxes, predictions):
    out = img_bgr.copy()
    
    for (x, y, w, h), (digit, conf) in zip(boxes, predictions):
        color = (80, 220, 80)
        cv2.rectangle(out, (x, y), (x + w, y + h), color, 2)
        
        label      = f"{digit}  {conf:.0f}%"
        font_scale = max(0.5, min(w, h) / 55)
        thickness  = max(1, int(font_scale * 2))
        
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX,
                                      font_scale, thickness)
        ty = max(y - 6, th + 4)
        
        cv2.rectangle(out, (x, ty - th - 4), (x + tw + 6, ty + 2),
                      color, cv2.FILLED)
        cv2.putText(out, label, (x + 3, ty - 2),
                    cv2.FONT_HERSHEY_SIMPLEX, font_scale,
                    (0, 0, 0), thickness, cv2.LINE_AA)
    
    base, ext = os.path.splitext(image_path)
    out_path  = base + "_predicted" + (ext or ".png")
    cv2.imwrite(out_path, out)
    
    return out_path

# ═══════════════════════════════════════════════════════════════════════════
# 4. MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main():
    if len(sys.argv) < 2:
        print("Usage: python predict_image.py <image_path>")
        sys.exit(1)
    
    image_path = sys.argv[1]
    if not os.path.exists(image_path):
        print(f"Error: '{image_path}' not found.")
        sys.exit(1)
    
    print("Loading model …", end=" ", flush=True)
    model = tf.keras.models.load_model(MODEL_PATH)
    print("done.\n")
    
    print(f"Segmenting '{image_path}' …")
    boxes, gray, img_bgr = segment_digits(image_path)
    
    if not boxes:
        print("No digits detected. Ensure dark digits on a light (or dark) background.")
        sys.exit(0)
    
    print(f"Detected {len(boxes)} digit(s).\n")
    
    print(f"  {'#':<5} {'Digit':<8} Confidence")
    print("  " + "─" * 28)
    
    predictions = []
    number_str  = ""
    
    for i, box in enumerate(boxes):
        arr   = preprocess_digit(gray, box)
        probs = model.predict(arr, verbose=0)[0]
        digit = int(np.argmax(probs))
        conf  = float(probs[digit]) * 100
        
        predictions.append((digit, conf))
        number_str += str(digit)
        
        print(f"  {i+1:<5} {digit:<8} {conf:.1f}%")
    
    print("  " + "─" * 28)
    print(f"\n  ✅  Digits read (L→R) : {number_str}")
    print(f"      Total detected   : {len(boxes)}\n")
    
    out_path = save_annotated(image_path, img_bgr, boxes, predictions)
    print(f"  Annotated image saved → {out_path}\n")

if __name__ == "__main__":
    main()