#!/usr/bin/env python3
"""
Debug Roll Number Detection
Test and debug the blue ink roll number detection system
"""
import os
import cv2
import numpy as np
from utils.roll_number_detector import RollNumberDetector

def debug_roll_detection():
    print("🔍 DEBUGGING ROLL NUMBER DETECTION")
    print("=" * 60)
    
    # Test images
    test_images = [
        "uploads/c-1.jpeg",
        "uploads/c-2.jpeg"
    ]
    
    # Initialize detector with debug mode
    try:
        config = {
            'debug_mode': True,  # Enable debug images
            'top_crop_fraction': 0.18,
            'right_crop_fraction': 0.40,
            'blue_hsv_lower': [90, 50, 50],
            'blue_hsv_upper': [135, 255, 255],
            'min_digit_area': 80,
            'max_digit_area': 50000,
            'min_confidence': 0.7
        }
        
        detector = RollNumberDetector("models/digit_recognizer.keras", config)
        print("✅ Roll number detector initialized with debug mode")
        
    except Exception as e:
        print(f"❌ Failed to initialize detector: {e}")
        return
    
    for image_path in test_images:
        if not os.path.exists(image_path):
            print(f"❌ Image not found: {image_path}")
            continue
        
        print(f"\n📸 Testing: {os.path.basename(image_path)}")
        print("-" * 40)
        
        # Test detection
        result = detector.detect_roll_number(image_path)
        
        print(f"   Roll Number: {result.roll_number}")
        print(f"   Confidence: {result.confidence:.3f}")
        print(f"   Processing Time: {result.processing_time:.3f}s")
        print(f"   Digit Confidences: {result.digit_confidences}")
        print(f"   Debug Info: {result.debug_info}")
        
        # Check if debug images were created
        debug_files = [
            "debug_1_top_right_crop.jpg",
            "debug_2_blue_mask.jpg", 
            "debug_3_digit_boxes.jpg"
        ]
        
        for debug_file in debug_files:
            if os.path.exists(debug_file):
                print(f"   📁 Created: {debug_file}")
            else:
                print(f"   ❌ Missing: {debug_file}")

def test_blue_ink_detection():
    """Test different HSV ranges for blue ink detection"""
    print("\n🔵 TESTING BLUE INK DETECTION PARAMETERS")
    print("=" * 60)
    
    test_image = "uploads/c-1.jpeg"
    if not os.path.exists(test_image):
        print(f"❌ Test image not found: {test_image}")
        return
    
    # Load and crop image
    image = cv2.imread(test_image)
    h, w = image.shape[:2]
    
    # Crop top-right region (same as detector)
    top = 0
    bottom = int(h * 0.18)
    left = int(w * 0.6)  # right 40%
    right = w
    region = image[top:bottom, left:right]
    
    print(f"   Original image: {image.shape}")
    print(f"   Cropped region: {region.shape}")
    
    # Test different HSV ranges
    hsv_ranges = [
        ("Default Blue", [90, 50, 50], [135, 255, 255]),
        ("Wider Blue", [80, 30, 30], [140, 255, 255]),
        ("Darker Blue", [100, 80, 80], [130, 255, 255]),
        ("All Blues", [90, 30, 30], [150, 255, 255]),
    ]
    
    hsv = cv2.cvtColor(region, cv2.COLOR_BGR2HSV)
    
    for name, lower, upper in hsv_ranges:
        mask = cv2.inRange(hsv, np.array(lower), np.array(upper))
        blue_pixels = np.count_nonzero(mask)
        
        print(f"   {name}: {blue_pixels} blue pixels")
        
        # Save debug image
        debug_filename = f"debug_blue_{name.lower().replace(' ', '_')}.jpg"
        cv2.imwrite(debug_filename, mask)
        print(f"      Saved: {debug_filename}")

def test_manual_crop_regions():
    """Test different crop regions to find roll numbers"""
    print("\n✂️ TESTING DIFFERENT CROP REGIONS")
    print("=" * 60)
    
    test_image = "uploads/c-1.jpeg"
    if not os.path.exists(test_image):
        print(f"❌ Test image not found: {test_image}")
        return
    
    image = cv2.imread(test_image)
    h, w = image.shape[:2]
    
    # Test different crop regions
    crop_regions = [
        ("Top-Right (18%, 40%)", 0, int(h * 0.18), int(w * 0.6), w),
        ("Top-Right (25%, 50%)", 0, int(h * 0.25), int(w * 0.5), w),
        ("Top-Center", 0, int(h * 0.2), int(w * 0.3), int(w * 0.7)),
        ("Top-Left", 0, int(h * 0.2), 0, int(w * 0.4)),
        ("Full Top", 0, int(h * 0.3), 0, w),
    ]
    
    for name, top, bottom, left, right in crop_regions:
        region = image[top:bottom, left:right]
        
        # Convert to HSV and detect blue
        hsv = cv2.cvtColor(region, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, np.array([90, 50, 50]), np.array([135, 255, 255]))
        blue_pixels = np.count_nonzero(mask)
        
        print(f"   {name}: {region.shape} -> {blue_pixels} blue pixels")
        
        # Save crop and mask
        crop_filename = f"debug_crop_{name.lower().replace(' ', '_').replace('(', '').replace(')', '').replace('%', 'pct').replace(',', '_')}.jpg"
        mask_filename = f"debug_mask_{name.lower().replace(' ', '_').replace('(', '').replace(')', '').replace('%', 'pct').replace(',', '_')}.jpg"
        
        cv2.imwrite(crop_filename, region)
        cv2.imwrite(mask_filename, mask)
        
        print(f"      Saved: {crop_filename}")
        print(f"      Saved: {mask_filename}")

if __name__ == "__main__":
    debug_roll_detection()
    test_blue_ink_detection()
    test_manual_crop_regions()