import cv2
import numpy as np
from skimage.morphology import skeletonize

def get_contours(image_path):
    img = cv2.imread(image_path)
    if img is None:
        return None, "Could not read image"
    
    # Resize to a standard width for consistent processing
    target_width = 1000
    h, w = img.shape[:2]
    scale = target_width / w
    dim = (target_width, int(h * scale))
    img = cv2.resize(img, dim, interpolation=cv2.INTER_AREA)
    
    # Convert to HSV
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    
    # Define range for red color
    # Red wraps around 0/180
    lower_red1 = np.array([0, 70, 50])
    upper_red1 = np.array([10, 255, 255])
    lower_red2 = np.array([170, 70, 50])
    upper_red2 = np.array([180, 255, 255])
    
    mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
    mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
    mask = mask1 + mask2
    
    # Morphological operations to clean up
    kernel = np.ones((3,3), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    
    # Find contours
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Filter contours based on area
    min_area = 50  # adjust based on image size
    valid_contours = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area > min_area:
            x, y, w, h = cv2.boundingRect(cnt)
            # Filter out very large contours (like headers if they are red)
            if w * h < 50000: 
                valid_contours.append(cnt)
    
    # Sort contours top to bottom
    valid_contours = sorted(valid_contours, key=lambda c: cv2.boundingRect(c)[1])
    
    return valid_contours, img

def classify_mark(contour, image):
    # Convexity Defects Method
    hull = cv2.convexHull(contour, returnPoints=False)
    if hull is None or len(hull) <= 3:
        return 1, "Tick" # Too simple to be a cross

    try:
        defects = cv2.convexityDefects(contour, hull)
    except Exception:
        return 1, "Tick"

    if defects is None:
        return 1, "Tick"

    # Count significant defects
    # Significant means depth is large enough
    x, y, w, h = cv2.boundingRect(contour)
    
    # Lowered threshold to 15% to detect shallower defects in crosses
    threshold_depth = min(w, h) * 0.15 
    
    count_defects = 0
    for i in range(defects.shape[0]):
        s, e, f, d = defects[i, 0]
        # d is distance in roughly 1/256 pixel units
        depth = d / 256.0
        if depth > threshold_depth:
            count_defects += 1
            
    # print(f"Debug: Shape at x={x} w={w} h={h} Defects={count_defects} Thresh={threshold_depth:.2f}")
    
    # Cross (X) usually has 4 defects. Squashed X or T has 2.
    # Tick (V) has 1 defect.
    # We lower the requirement to >= 2 to catch messy/squashed crosses.
    
    if count_defects >= 2:
        return 0, "Cross"
    else:
        return 1, "Tick"

def process_image(image_path):
    contours, img = get_contours(image_path)
    if contours is None:
        return []
    
    results = []
    for i, cnt in enumerate(contours):
        mark, label = classify_mark(cnt, img)
        results.append({
            "question_index": i + 1,
            "mark": mark,
            "label": label,
            "contour": cnt # Keep for debug/visualization if needed
        })
    return results
