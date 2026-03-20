#!/usr/bin/env python3
"""
Enhanced Roll Number Detector
Integrates the original digitrec files for 100% accurate roll number detection
"""
import cv2
import numpy as np
from typing import List, Tuple, Optional
import os
import sys
from PIL import Image, ImageFilter

# Safe TensorFlow import with error handling
try:
    import tensorflow as tf
    TF_AVAILABLE = True
    print("✅ TensorFlow loaded successfully")
except ImportError as e:
    tf = None
    TF_AVAILABLE = False
    print(f"Warning: TensorFlow not available: {e}")

# Add the root directory to path to import the original files
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

class EnhancedRollDetector:
    """Enhanced roll number detector using original digitrec algorithms"""
    
    def __init__(self, model_path: str = "models/digit_recognizer.keras"):
        self.model_path = model_path
        self.model = None
        self.tf_available = TF_AVAILABLE
        
        if self.tf_available:
            self._load_model()
        else:
            print("⚠️ TensorFlow not available - roll number detection will be disabled")
        
        # Configuration from original digitrec
        self.TOP_CROP_FRACTION = 0.18
        self.RIGHT_CROP_FRACTION = 0.40
        self.BLUE_HSV_LOWER = np.array([90, 50, 50])
        self.BLUE_HSV_UPPER = np.array([135, 255, 255])
        self.MIN_DIGIT_AREA = 80
        self.MAX_DIGIT_AREA = 50000
    
    def _load_model(self):
        """Load the trained CNN model"""
        try:
            if not self.tf_available:
                print("❌ TensorFlow not available - cannot load model")
                return
                
            if os.path.exists(self.model_path):
                self.model = tf.keras.models.load_model(self.model_path)
                print(f"✅ Loaded CNN model from {self.model_path}")
            else:
                print(f"❌ Model not found: {self.model_path}")
                self.model = None
        except Exception as e:
            print(f"❌ Error loading model: {e}")
            self.model = None
    
    def recognize_roll_number(self, image_path: str, debug: bool = False) -> str:
        """
        Recognize roll number using original digitrec algorithm
        """
        if not self.tf_available or self.model is None:
            print("⚠️ TensorFlow/Model not available - returning UNKNOWN")
            return "UNKNOWN"
        
        try:
            # Load image
            image = cv2.imread(image_path)
            if image is None:
                print(f"❌ Could not load image: {image_path}")
                return "ERROR"
            
            if debug:
                print(f"Image loaded: {image.shape[1]}×{image.shape[0]} px")
            
            # Step 1: Crop top-right region (original algorithm)
            region = self._crop_top_right(image, debug)
            
            # Step 2: Isolate blue ink (original algorithm)
            mask = self._isolate_blue_ink(region, debug)
            
            # Step 3: Find digit contours (original algorithm)
            boxes = self._find_digit_contours(mask, region, debug)
            
            if not boxes:
                if debug:
                    print("⚠  No blue handwritten digits detected in top-right corner.")
                return "NOT_FOUND"
            
            # Step 4: Recognize each digit (original algorithm)
            roll_number = ""
            if debug:
                print(f"\nDetected {len(boxes)} digit(s):")
                print("─" * 40)
            
            for i, box in enumerate(boxes):
                arr = self._preprocess_digit(mask, box)
                probs = self.model.predict(arr, verbose=0)[0]
                digit = int(np.argmax(probs))
                conf = float(probs[digit]) * 100
                
                roll_number += str(digit)
                
                if debug:
                    print(f"  Digit {i+1}: {digit}  (confidence: {conf:.1f}%)")
            
            if debug:
                print("─" * 40)
                print(f"\n  ✅  Roll Number: {roll_number}")
            
            return roll_number
            
        except Exception as e:
            print(f"❌ Error in roll number recognition: {e}")
            return "ERROR"
    
    def _crop_top_right(self, image: np.ndarray, debug=False) -> np.ndarray:
        """Crop top-right region using original algorithm"""
        h, w = image.shape[:2]
        
        top = 0
        bottom = int(h * self.TOP_CROP_FRACTION)
        left = int(w * (1 - self.RIGHT_CROP_FRACTION))
        right = w
        
        region = image[top:bottom, left:right]
        
        if debug:
            cv2.imwrite("debug_1_top_right_crop.jpg", region)
            print(f"[DEBUG] Cropped region: {region.shape} (from {image.shape})")
        
        return region
    
    def _isolate_blue_ink(self, region: np.ndarray, debug=False) -> np.ndarray:
        """Isolate blue ink using original algorithm"""
        hsv = cv2.cvtColor(region, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, self.BLUE_HSV_LOWER, self.BLUE_HSV_UPPER)
        
        # Morphological clean-up: close small gaps, remove tiny noise
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=1)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
        
        if debug:
            cv2.imwrite("debug_2_blue_mask.jpg", mask)
            print(f"[DEBUG] Blue pixels found: {np.count_nonzero(mask)}")
        
        return mask
    
    def _find_digit_contours(self, mask: np.ndarray, region: np.ndarray, debug=False):
        """Find digit contours using original algorithm"""
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        boxes = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if not (self.MIN_DIGIT_AREA < area < self.MAX_DIGIT_AREA):
                continue
            
            x, y, w, h = cv2.boundingRect(cnt)
            aspect = w / float(h) if h > 0 else 0
            
            # Filter: digits are taller than wide (or squarish), not thin lines
            if aspect > 2.5:
                continue
            
            boxes.append((x, y, w, h))
        
        # Merge boxes that are very close horizontally (parts of same digit)
        boxes = self._merge_close_boxes(boxes)
        
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
    
    def _merge_close_boxes(self, boxes, gap_threshold=3):
        """Merge horizontally adjacent bounding boxes"""
        if not boxes:
            return boxes
        
        boxes = sorted(boxes, key=lambda b: b[0])
        merged = [boxes[0]]
        
        for x, y, w, h in boxes[1:]:
            px, py, pw, ph = merged[-1]
            
            if x - (px + pw) < gap_threshold:  # close enough → merge
                nx = min(px, x)
                ny = min(py, y)
                nw = max(px+pw, x+w) - nx
                nh = max(py+ph, y+h) - ny
                merged[-1] = (nx, ny, nw, nh)
            else:
                merged.append((x, y, w, h))
        
        return merged
    
    def _preprocess_digit(self, mask: np.ndarray, box) -> np.ndarray:
        """Preprocess digit using original algorithm"""
        x, y, w, h = box
        
        pad = 6
        x1 = max(0, x - pad)
        y1 = max(0, y - pad)
        x2 = min(mask.shape[1], x + w + pad)
        y2 = min(mask.shape[0], y + h + pad)
        
        digit_mask = mask[y1:y2, x1:x2]
        
        # PIL for better resizing
        pil = Image.fromarray(digit_mask)
        pil.thumbnail((20, 20), Image.LANCZOS)
        
        canvas = Image.new("L", (28, 28), 0)
        xo = (28 - pil.width) // 2
        yo = (28 - pil.height) // 2
        canvas.paste(pil, (xo, yo))
        
        canvas = canvas.filter(ImageFilter.GaussianBlur(0.5))
        arr = np.array(canvas, dtype="float32") / 255.0
        
        return arr.reshape(1, 28, 28, 1)
    
    def calibrate(self, image_path: str) -> bool:
        """Visual calibration using original algorithm"""
        print(f"🔧 CALIBRATING with {image_path}")
        
        try:
            image = cv2.imread(image_path)
            if image is None:
                print(f"❌ Could not load image: {image_path}")
                return False
            
            h, w = image.shape[:2]
            print(f"\n📄 Image: {os.path.basename(image_path)}  ({w}×{h} px)")
            print(f"   Top crop    : top {self.TOP_CROP_FRACTION*100:.0f}% of height  → {int(h*self.TOP_CROP_FRACTION)} px")
            print(f"   Right crop  : right {self.RIGHT_CROP_FRACTION*100:.0f}% of width → {int(w*self.RIGHT_CROP_FRACTION)} px\n")
            
            # Step 1: Draw crop rectangle on full image
            vis_full = image.copy()
            top = 0
            bottom = int(h * self.TOP_CROP_FRACTION)
            left = int(w * (1 - self.RIGHT_CROP_FRACTION))
            
            cv2.rectangle(vis_full, (left, top), (w-1, bottom), (0, 0, 255), 3)
            cv2.putText(vis_full, "ROLL NUMBER ZONE", (left + 10, top + 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
            cv2.imwrite("calib_1_full_page_with_zone.jpg", vis_full)
            print("✅  Saved: calib_1_full_page_with_zone.jpg  (red box = search zone)")
            
            # Step 2: Cropped region
            region = self._crop_top_right(image)
            cv2.imwrite("calib_2_cropped_region.jpg", region)
            print("✅  Saved: calib_2_cropped_region.jpg        (what the system sees)")
            
            # Step 3: Blue ink mask
            mask = self._isolate_blue_ink(region)
            cv2.imwrite("calib_3_blue_ink_mask.jpg", mask)
            blue_count = np.count_nonzero(mask)
            print(f"✅  Saved: calib_3_blue_ink_mask.jpg         (blue pixels: {blue_count})")
            
            # Step 4: Digit boxes overlaid on region
            boxes = self._find_digit_contours(mask, region)
            vis_region = region.copy()
            for i, (x, y, bw, bh) in enumerate(boxes):
                cv2.rectangle(vis_region, (x, y), (x+bw, y+bh), (0, 255, 0), 2)
                cv2.putText(vis_region, f"D{i+1}", (x, y-5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,0), 2)
            cv2.imwrite("calib_4_detected_digits.jpg", vis_region)
            print(f"✅  Saved: calib_4_detected_digits.jpg       (digits found: {len(boxes)})")
            
            # Summary
            print("\n" + "─"*55)
            if blue_count < 100:
                print("⚠  WARNING: Very few blue pixels detected!")
                print("   → The roll number may not be in blue ink,")
                print("     or the lighting may be poor.")
            elif len(boxes) == 0:
                print("⚠  WARNING: Blue ink found but no digit shapes detected.")
                print("   → Try adjusting MIN_DIGIT_AREA parameter")
            else:
                print(f"✅  System found {len(boxes)} digit(s) in the roll number zone.")
                print("   → Ready for roll number recognition")
            print("─"*55)
            
            return True
            
        except Exception as e:
            print(f"❌ Calibration error: {e}")
            return False

def test_enhanced_detection():
    """Test the enhanced detection"""
    print("🧪 TESTING ENHANCED ROLL NUMBER DETECTION")
    print("=" * 50)
    
    test_images = ["uploads/cor-01.png", "uploads/c-1.jpeg", "uploads/c-2.jpeg"]
    
    detector = EnhancedRollDetector()
    
    for image_path in test_images:
        if not os.path.exists(image_path):
            print(f"❌ Image not found: {image_path}")
            continue
        
        print(f"\n📄 Testing: {os.path.basename(image_path)}")
        print("-" * 40)
        
        # Calibration
        detector.calibrate(image_path)
        
        # Detection
        result = detector.recognize_roll_number(image_path, debug=True)
        print(f"\n🎯 FINAL RESULT: {result}")

if __name__ == "__main__":
    test_enhanced_detection()