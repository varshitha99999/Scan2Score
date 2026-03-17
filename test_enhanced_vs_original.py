#!/usr/bin/env python3
"""
Compare enhanced vs original red ink processing
"""
import cv2
import numpy as np
from utils.image_processing import process_image, process_image_with_debug

def test_original_method(image_path):
    """Test the original method manually"""
    img = cv2.imread(image_path)
    if img is None:
        return []
    
    # Resize to standard width
    target_width = 1000
    h, w = img.shape[:2]
    scale = target_width / w
    dim = (target_width, int(h * scale))
    img = cv2.resize(img, dim, interpolation=cv2.INTER_AREA)
    
    # Original HSV red detection
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    
    lower_red1 = np.array([0, 70, 50])
    upper_red1 = np.array([10, 255, 255])
    lower_red2 = np.array([170, 70, 50])
    upper_red2 = np.array([180, 255, 255])
    
    mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
    mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
    mask = mask1 + mask2
    
    # Original morphological operations
    kernel = np.ones((3,3), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    
    # Find contours
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Original filtering
    min_area = 50
    valid_contours = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area > min_area:
       