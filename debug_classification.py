#!/usr/bin/env python3
"""
Debug the classification step to see why all marks are showing as 0
"""
import cv2
import numpy as np
import os
from utils.image_processing import get_contours, classify_mark

def debug_classification(image_path):
    """Debug classification step by step"""
    print(f"🔍 DEBUGGING CLASSIFICATION: {image_path}")
    print("=" * 50)
    
    # Get contours using the working method
    contours, img = get_contours(image_path)
    
    if contours is None:
        print("❌ No contours found!")
        return
    
    print(f"✅ Found {len(contours)} contours")
    
    # Test classification on each contour
    for i, cnt in enumerate(contours):
        print(f"\n📊 CONTOUR {i+1}:")
        print("-" * 20)
        
        # Get basic properties
        area = cv2.contourArea(cnt)
        x, y, w, h = cv2.boundingRect(cnt)
        
        print(f"   Area: {area:.1f}")
        print(f"   Bounding box: ({x}, {y}, {w}, {h})")
        print(f"   Aspect ratio: {max(w,h)/max(min(w,h),1):.2f}")
        
        # Test classification
        try:
            mark, label = classify_mark(cnt, img)
            print(f"   Classification: {label} -> {mark}")
            
            # Test individual scoring methods
            defect_score = analyze_convexity_defects_enhanced(cnt)
            shape_score = analyze_shape_properties(cnt)
            approx_score = analyze_contour_approximation_enhanced(cnt)
            area_score = analyze_area_properties(cnt)
            
            final_score = (
                defect_score * 0.4 +
                shape_score * 0.3 +
                approx_score * 0.2 +
                area_score * 0.1
            )
            
            print(f"   Defect score: {defect_score:.3f}")
            print(f"   Shape score: {shape_score:.3f}")
            print(f"   Approx score: {approx_score:.3f}")
            print(f"   Area score: {area_score:.3f}")
            print(f"   Final score: {final_score:.3f} (threshold: 0.6)")
            
        except Exception as e:
            print(f"   ❌ Classification error: {e}")
            import traceback
            traceback.print_exc()

def analyze_convexity_defects_enhanced(contour):
    """Test the enhanced convexity defects analysis"""
    hull = cv2.convexHull(contour, returnPoints=False)
    if hull is None or len(hull) <= 3:
        return 0.0
    
    try:
        defects = cv2.convexityDefects(contour, hull)
    except Exception:
        return 0.0
    
    if defects is None:
        return 0.0
    
    x, y, w, h = cv2.boundingRect(contour)
    size_factor = min(w, h)
    threshold_depth = size_factor * 0.2
    
    significant_defects = 0
    for i in range(defects.shape[0]):
        s, e, f, d = defects[i, 0]
        depth = d / 256.0
        if depth > threshold_depth:
            significant_defects += 1
    
    if significant_defects == 0:
        return 0.0
    elif significant_defects == 1:
        return 0.3
    elif significant_defects == 2:
        return 0.7
    else:
        return 1.0

def analyze_shape_properties(contour):
    """Test shape properties analysis"""
    try:
        area = cv2.contourArea(contour)
        x, y, w, h = cv2.boundingRect(contour)
        
        if area == 0 or w == 0 or h == 0:
            return 0.5
        
        aspect_ratio = max(w, h) / min(w, h)
        extent = area / (w * h)
        
        cross_score = 0
        
        if 0.8 <= aspect_ratio <= 1.5:
            cross_score += 0.4
        elif aspect_ratio > 2.0:
            cross_score -= 0.2
        
        if extent < 0.5:
            cross_score += 0.4
        elif extent > 0.7:
            cross_score -= 0.2
        
        return max(0, min(1, cross_score + 0.2))
        
    except Exception:
        return 0.5

def analyze_contour_approximation_enhanced(contour):
    """Test contour approximation analysis"""
    try:
        epsilon = 0.02 * cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, epsilon, True)
        corner_count = len(approx)
        
        if corner_count <= 4:
            return 0.2
        elif corner_count <= 6:
            return 0.5
        else:
            return 0.8
            
    except Exception:
        return 0.5

def analyze_area_properties(contour):
    """Test area properties analysis"""
    try:
        area = cv2.contourArea(contour)
        hull = cv2.convexHull(contour)
        hull_area = cv2.contourArea(hull)
        
        if hull_area == 0:
            return 0.5
        
        solidity = area / hull_area
        
        if solidity < 0.7:
            return 0.7
        elif solidity > 0.9:
            return 0.2
        else:
            return 0.5
            
    except Exception:
        return 0.5

def test_classification_on_all():
    """Test classification on all images"""
    test_images = [
        "uploads/c-1.jpeg",
        "uploads/c-2.jpeg",
        "test_marks.jpg"
    ]
    
    for img_path in test_images:
        if os.path.exists(img_path):
            debug_classification(img_path)
            print("\n" + "="*60 + "\n")

if __name__ == "__main__":
    test_classification_on_all()