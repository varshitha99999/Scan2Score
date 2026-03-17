#!/usr/bin/env python3
"""
Fix Roll Number Detection
Adjust parameters to make roll number detection work correctly
"""
import os
import cv2
import numpy as np
from utils.roll_number_detector import RollNumberDetector

def test_with_adjusted_parameters():
    print("🔧 TESTING WITH ADJUSTED PARAMETERS")
    print("=" * 50)
    
    test_image = "uploads/c-1.jpeg"
    
    if not os.path.exists(test_image):
        print(f"❌ Test image not found: {test_image}")
        return
    
    # Try different parameter sets
    parameter_sets = [
        {
            'name': 'More Lenient Areas',
            'config': {
                'top_crop_fraction': 0.18,
                'right_crop_fraction': 0.40,
                'blue_hsv_lower': [90, 50, 50],
                'blue_hsv_upper': [135, 255, 255],
                'min_digit_area': 20,      # Reduced from 80
                'max_digit_area': 50000,
                'min_confidence': 0.5,     # Reduced from 0.7
                'merge_gap_threshold': 5,
                'aspect_ratio_filter': 3.0,
                'debug_mode': True
            }
        },
        {
            'name': 'Wider Blue Range',
            'config': {
                'top_crop_fraction': 0.18,
                'right_crop_fraction': 0.40,
                'blue_hsv_lower': [80, 30, 30],  # Wider range
                'blue_hsv_upper': [140, 255, 255],
                'min_digit_area': 20,
                'max_digit_area': 50000,
                'min_confidence': 0.5,
                'merge_gap_threshold': 5,
                'aspect_ratio_filter': 3.0,
                'debug_mode': True
            }
        },
        {
            'name': 'Larger Crop Area',
            'config': {
                'top_crop_fraction': 0.25,    # Larger crop
                'right_crop_fraction': 0.50,  # Larger crop
                'blue_hsv_lower': [80, 30, 30],
                'blue_hsv_upper': [140, 255, 255],
                'min_digit_area': 20,
                'max_digit_area': 50000,
                'min_confidence': 0.5,
                'merge_gap_threshold': 5,
                'aspect_ratio_filter': 3.0,
                'debug_mode': True
            }
        }
    ]
    
    for param_set in parameter_sets:
        print(f"\n🧪 Testing: {param_set['name']}")
        print("-" * 30)
        
        try:
            detector = RollNumberDetector("models/digit_recognizer.keras", param_set['config'])
            result = detector.detect_roll_number(test_image)
            
            print(f"   Roll Number: {result.roll_number}")
            print(f"   Confidence: {result.confidence:.3f}")
            print(f"   Debug Info: {result.debug_info}")
            
            if result.roll_number != "NOT_FOUND" and result.roll_number != "ERROR":
                print(f"   ✅ SUCCESS! Detected roll number: {result.roll_number}")
                return param_set['config']  # Return working config
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    return None

def manual_contour_analysis():
    """Manually analyze contours to understand the issue"""
    print("\n🔍 MANUAL CONTOUR ANALYSIS")
    print("=" * 40)
    
    test_image = "uploads/c-1.jpeg"
    
    if not os.path.exists(test_image):
        print(f"❌ Test image not found: {test_image}")
        return
    
    # Load and process image manually
    image = cv2.imread(test_image)
    h, w = image.shape[:2]
    
    # Crop top-right region
    top = 0
    bottom = int(h * 0.18)
    left = int(w * 0.6)
    right = w
    region = image[top:bottom, left:right]
    
    print(f"   Region shape: {region.shape}")
    
    # Convert to HSV and create mask
    hsv = cv2.cvtColor(region, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, np.array([80, 30, 30]), np.array([140, 255, 255]))
    
    # Find contours
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    print(f"   Total contours found: {len(contours)}")
    
    # Analyze each contour
    valid_contours = 0
    for i, cnt in enumerate(contours):
        area = cv2.contourArea(cnt)
        x, y, w, h = cv2.boundingRect(cnt)
        aspect = w / float(h) if h > 0 else 0
        
        print(f"   Contour {i}: area={area:.1f}, bbox=({x},{y},{w},{h}), aspect={aspect:.2f}")
        
        # Check if it would pass filters
        if area > 20 and area < 50000 and aspect < 3.0:
            valid_contours += 1
            print(f"      ✅ Valid contour")
        else:
            print(f"      ❌ Filtered out")
    
    print(f"   Valid contours: {valid_contours}")
    
    # Save debug images
    cv2.imwrite("manual_debug_region.jpg", region)
    cv2.imwrite("manual_debug_mask.jpg", mask)
    
    # Draw all contours
    vis = region.copy()
    cv2.drawContours(vis, contours, -1, (0, 255, 0), 2)
    cv2.imwrite("manual_debug_contours.jpg", vis)
    
    print(f"   Saved debug images: manual_debug_*.jpg")

if __name__ == "__main__":
    # Test with adjusted parameters
    working_config = test_with_adjusted_parameters()
    
    # Manual analysis
    manual_contour_analysis()
    
    if working_config:
        print(f"\n✅ FOUND WORKING CONFIGURATION:")
        for key, value in working_config.items():
            print(f"   {key}: {value}")
    else:
        print(f"\n❌ No working configuration found. Check manual analysis results.")