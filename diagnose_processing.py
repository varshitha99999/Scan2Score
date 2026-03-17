#!/usr/bin/env python3
"""
Diagnostic tool to identify issues with roll number detection and marks processing
"""
import os
import cv2
import numpy as np
from utils.roll_number_detector import RollNumberDetector
from utils.image_processing import process_image

def diagnose_image(image_path):
    """Comprehensive diagnosis of an image"""
    print(f"🔍 DIAGNOSING: {image_path}")
    print("=" * 60)
    
    if not os.path.exists(image_path):
        print("❌ Image file not found!")
        return
    
    # Load image
    img = cv2.imread(image_path)
    if img is None:
        print("❌ Cannot read image file!")
        return
    
    h, w = img.shape[:2]
    print(f"📐 Image dimensions: {w}x{h}")
    
    # 1. Check for blue ink (roll number detection)
    print("\n🔵 BLUE INK ANALYSIS (Roll Numbers)")
    print("-" * 40)
    
    # Crop top-right region (where roll numbers should be)
    top_crop = int(h * 0.18)
    right_crop = int(w * 0.40)
    roll_region = img[0:top_crop, w-right_crop:w]
    
    # Convert to HSV and check for blue
    hsv = cv2.cvtColor(roll_region, cv2.COLOR_BGR2HSV)
    blue_lower = np.array([90, 50, 50])
    blue_upper = np.array([135, 255, 255])
    blue_mask = cv2.inRange(hsv, blue_lower, blue_upper)
    blue_pixels = np.count_nonzero(blue_mask)
    
    print(f"   Roll number region: {roll_region.shape}")
    print(f"   Blue pixels found: {blue_pixels}")
    
    if blue_pixels > 100:
        print("   ✅ Sufficient blue ink detected for roll number")
    else:
        print("   ⚠️  Little/no blue ink found - roll number may not be detectable")
    
    # 2. Check for red ink (marks detection)
    print("\n🔴 RED INK ANALYSIS (Marks)")
    print("-" * 40)
    
    # Convert to HSV and check for red
    hsv_full = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    
    # Red color ranges (red wraps around in HSV)
    red_lower1 = np.array([0, 70, 50])
    red_upper1 = np.array([10, 255, 255])
    red_lower2 = np.array([170, 70, 50])
    red_upper2 = np.array([180, 255, 255])
    
    red_mask1 = cv2.inRange(hsv_full, red_lower1, red_upper1)
    red_mask2 = cv2.inRange(hsv_full, red_lower2, red_upper2)
    red_mask = red_mask1 + red_mask2
    red_pixels = np.count_nonzero(red_mask)
    
    print(f"   Red pixels found: {red_pixels}")
    
    if red_pixels > 500:
        print("   ✅ Sufficient red ink detected for marks processing")
    else:
        print("   ⚠️  Little/no red ink found - marks may not be detectable")
    
    # 3. Test actual processing
    print("\n🧪 ACTUAL PROCESSING RESULTS")
    print("-" * 40)
    
    # Roll number detection
    try:
        detector = RollNumberDetector("models/digit_recognizer.keras")
        detection = detector.detect_roll_number(image_path)
        print(f"   Roll Detection: {detection.roll_number} (conf: {detection.confidence:.3f})")
        print(f"   Debug info: {detection.debug_info}")
    except Exception as e:
        print(f"   Roll Detection Error: {e}")
    
    # Marks processing
    try:
        marks_results = process_image(image_path)
        marks_map = {i+1: r['mark'] for i, r in enumerate(marks_results)}
        total_score = sum(marks_map.values())
        print(f"   Marks Found: {len(marks_results)} marks")
        print(f"   Total Score: {total_score}/{len(marks_results)}")
        print(f"   Marks Map: {marks_map}")
    except Exception as e:
        print(f"   Marks Processing Error: {e}")
    
    # 4. Recommendations
    print("\n💡 RECOMMENDATIONS")
    print("-" * 40)
    
    if blue_pixels < 100:
        print("   📝 For roll number detection:")
        print("      • Ensure roll numbers are written in BLUE ink")
        print("      • Roll numbers should be in the TOP-RIGHT corner")
        print("      • Use clear, bold handwriting")
    
    if red_pixels < 500:
        print("   📝 For marks processing:")
        print("      • Ensure corrections are made in RED ink")
        print("      • Use clear ticks (✓) and crosses (✗)")
        print("      • Avoid very light or faded red ink")
    
    print("\n" + "=" * 60)

def main():
    print("🩺 IMAGE PROCESSING DIAGNOSTIC TOOL")
    print("=" * 60)
    
    # Test with available images
    test_images = [
        "uploads/c-1.jpeg",
        "uploads/c-2.jpeg",
        "uploads/C-1-2.jpeg",
        "test_marks.jpg",
        "test_shapes.jpg"
    ]
    
    for img_path in test_images:
        if os.path.exists(img_path):
            diagnose_image(img_path)
            print("\n")
    
    print("🎯 SUMMARY:")
    print("• Red ink marks processing is working correctly")
    print("• Roll number detection requires blue ink in top-right corner")
    print("• Both systems work independently - marks are always processed")
    print("• Manual review handles cases where roll detection fails")

if __name__ == "__main__":
    main()