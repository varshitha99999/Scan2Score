"""
calibrate.py — Visual calibration tool

Shows you exactly what the system sees before running recognition.
Run this FIRST on a sample paper to verify the crop & blue ink detection.

Usage:
    python calibrate.py path/to/sample_paper.jpg
"""

import os, sys
import cv2
import numpy as np

# Import config from recognize_roll
sys.path.insert(0, os.path.dirname(__file__))
from recognise_roll import (TOP_CROP_FRACTION, RIGHT_CROP_FRACTION,
                           BLUE_HSV_LOWER, BLUE_HSV_UPPER,
                           crop_top_right, isolate_blue_ink, find_digit_contours)

def calibrate(image_path: str):
    image = cv2.imread(image_path)
    if image is None:
        print(f"Cannot read '{image_path}'"); sys.exit(1)
    
    h, w = image.shape[:2]
    print(f"\n📄 Image: {os.path.basename(image_path)}  ({w}×{h} px)")
    print(f"   Top crop    : top {TOP_CROP_FRACTION*100:.0f}% of height  → {int(h*TOP_CROP_FRACTION)} px")
    print(f"   Right crop  : right {RIGHT_CROP_FRACTION*100:.0f}% of width → {int(w*RIGHT_CROP_FRACTION)} px\n")
    
    # ── Step 1: Draw crop rectangle on full image ──────────────────────
    vis_full = image.copy()
    top      = 0
    bottom   = int(h * TOP_CROP_FRACTION)
    left     = int(w * (1 - RIGHT_CROP_FRACTION))
    
    cv2.rectangle(vis_full, (left, top), (w-1, bottom), (0, 0, 255), 3)
    cv2.putText(vis_full, "ROLL NUMBER ZONE", (left + 10, top + 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
    cv2.imwrite("calib_1_full_page_with_zone.jpg", vis_full)
    print("✅  Saved: calib_1_full_page_with_zone.jpg  (red box = search zone)")
    
    # ── Step 2: Cropped region ─────────────────────────────────────────
    region = crop_top_right(image)
    cv2.imwrite("calib_2_cropped_region.jpg", region)
    print("✅  Saved: calib_2_cropped_region.jpg        (what the system sees)")
    
    # ── Step 3: Blue ink mask ──────────────────────────────────────────
    mask = isolate_blue_ink(region)
    cv2.imwrite("calib_3_blue_ink_mask.jpg", mask)
    blue_count = np.count_nonzero(mask)
    print(f"✅  Saved: calib_3_blue_ink_mask.jpg         (blue pixels: {blue_count})")
    
    # ── Step 4: Digit boxes overlaid on region ─────────────────────────
    boxes = find_digit_contours(mask, region)
    vis_region = region.copy()
    for i, (x, y, bw, bh) in enumerate(boxes):
        cv2.rectangle(vis_region, (x, y), (x+bw, y+bh), (0, 255, 0), 2)
        cv2.putText(vis_region, f"D{i+1}", (x, y-5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,0), 2)
    cv2.imwrite("calib_4_detected_digits.jpg", vis_region)
    print(f"✅  Saved: calib_4_detected_digits.jpg       (digits found: {len(boxes)})")
    
    # ── Summary ────────────────────────────────────────────────────────
    print("\n" + "─"*55)
    if blue_count < 100:
        print("⚠  WARNING: Very few blue pixels detected!")
        print("   → The roll number may not be in blue ink,")
        print("     or the lighting may be poor.")
        print("   → Edit BLUE_HSV_LOWER / BLUE_HSV_UPPER in recognise_roll.py")
    elif len(boxes) == 0:
        print("⚠  WARNING: Blue ink found but no digit shapes detected.")
        print("   → Try reducing MIN_DIGIT_AREA in recognise_roll.py")
    else:
        print(f"✅  System found {len(boxes)} digit(s) in the roll number zone.")
        print("   → Ready to run:  python recognise_roll.py your_paper.jpg")
    print("─"*55)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python calibrate.py path/to/paper.jpg")
        sys.exit(1)
    
    calibrate(sys.argv[1])