#!/usr/bin/env python3
"""
Debug red ink detection to identify why marks are showing as 0
"""
import cv2
import numpy as np
import os

def debug_red_detection(image_path):
    """Debug red ink detection step by step"""
    print(f"🔍 DEBUGGING RED INK DETECTION: {image_path}")
    print("=" * 50)
    
    if not os.path.exists(image_path):
        print("❌ Image file not found!")
        return
    
    # Load image
    img = cv2.imread(image_path)
    if img is None:
        print("❌ Cannot read image file!")
        return
    
    print(f"✅ Image loaded: {img.shape}")
    
    # Resize to standard width
    target_width = 1000
    h, w = img.shape[:2]
    scale = target_width / w
    dim = (target_width, int(h * scale))
    img_resized = cv2.resize(img, dim, interpolation=cv2.INTER_AREA)
    print(f"✅ Image resized: {img_resized.shape}")
    
    # Test original HSV method
    print("\n🔴 TESTING ORIGINAL HSV METHOD")
    print("-" * 30)
    
    hsv = cv2.cvtColor(img_resized, cv2.COLOR_BGR2HSV)
    
    # Original red ranges
    lower_red1 = np.array([0, 70, 50])
    upper_red1 = np.array([10, 255, 255])
    lower_red2 = np.array([170, 70, 50])
    upper_red2 = np.array([180, 255, 255])
    
    mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
    mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
    mask_hsv = mask1 + mask2
    
    red_pixels_hsv = np.count_nonzero(mask_hsv)
    print(f"Red pixels (HSV method): {red_pixels_hsv}")
    
    # Apply morphological operations
    kernel = np.ones((3,3), np.uint8)
    mask_cleaned = cv2.morphologyEx(mask_hsv, cv2.MORPH_OPEN, kernel)
    mask_cleaned = cv2.morphologyEx(mask_cleaned, cv2.MORPH_CLOSE, kernel)
    
    red_pixels_cleaned = np.count_nonzero(mask_cleaned)
    print(f"Red pixels after morphology: {red_pixels_cleaned}")
    
    # Find contours
    contours, _ = cv2.findContours(mask_cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    print(f"Total contours found: {len(contours)}")
    
    # Filter contours (original method)
    min_area = 50
    valid_contours = []
    for i, cnt in enumerate(contours):
        area = cv2.contourArea(cnt)
        x, y, w, h = cv2.boundingRect(cnt)
        print(f"  Contour {i}: area={area:.1f}, bbox=({x},{y},{w},{h})")
        
        if area > min_area:
            if w * h < 50000:
                valid_contours.append(cnt)
                print(f"    ✅ Valid contour")
            else:
                print(f"    ❌ Too large (area: {w*h})")
        else:
            print(f"    ❌ Too small (min: {min_area})")
    
    print(f"Valid contours: {len(valid_contours)}")
    
    # Test different red detection ranges
    print("\n🔴 TESTING DIFFERENT RED RANGES")
    print("-" * 30)
    
    # More lenient red ranges
    test_ranges = [
        ("Conservative", [0, 50, 50], [10, 255, 255], [170, 50, 50], [180, 255, 255]),
        ("Moderate", [0, 30, 30], [15, 255, 255], [165, 30, 30], [180, 255, 255]),
        ("Liberal", [0, 20, 20], [20, 255, 255], [160, 20, 20], [180, 255, 255]),
    ]
    
    for name, lower1, upper1, lower2, upper2 in test_ranges:
        mask1_test = cv2.inRange(hsv, np.array(lower1), np.array(upper1))
        mask2_test = cv2.inRange(hsv, np.array(lower2), np.array(upper2))
        mask_test = mask1_test + mask2_test
        
        red_pixels_test = np.count_nonzero(mask_test)
        contours_test, _ = cv2.findContours(mask_test, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        print(f"{name:12}: {red_pixels_test:6d} red pixels, {len(contours_test):3d} contours")
    
    # Save debug images
    base_name = os.path.splitext(os.path.basename(image_path))[0]
    cv2.imwrite(f"debug_red_{base_name}_original.jpg", img_resized)
    cv2.imwrite(f"debug_red_{base_name}_mask.jpg", mask_cleaned)
    
    # Create visualization with contours
    debug_img = img_resized.copy()
    for i, cnt in enumerate(valid_contours):
        cv2.drawContours(debug_img, [cnt], -1, (0, 255, 0), 2)
        x, y, w, h = cv2.boundingRect(cnt)
        cv2.putText(debug_img, str(i+1), (x, y-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
    
    cv2.imwrite(f"debug_red_{base_name}_contours.jpg", debug_img)
    
    print(f"\n💾 Debug images saved:")
    print(f"   debug_red_{base_name}_original.jpg")
    print(f"   debug_red_{base_name}_mask.jpg")
    print(f"   debug_red_{base_name}_contours.jpg")
    
    return len(valid_contours)

def test_all_images():
    """Test red detection on all available images"""
    test_images = [
        "uploads/c-1.jpeg",
        "uploads/c-2.jpeg",
        "uploads/C-1-2.jpeg",
        "test_marks.jpg",
        "test_shapes.jpg"
    ]
    
    print("🧪 TESTING RED INK DETECTION ON ALL IMAGES")
    print("=" * 60)
    
    for img_path in test_images:
        if os.path.exists(img_path):
            contour_count = debug_red_detection(img_path)
            print(f"Result: {contour_count} valid contours detected\n")
        else:
            print(f"⚠️  Image not found: {img_path}\n")

if __name__ == "__main__":
    test_all_images()