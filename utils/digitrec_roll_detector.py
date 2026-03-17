#!/usr/bin/env python3
"""
Roll Number Recognizer — Blue Ink, Top-Right Corner
Based on the exact approach from https://github.com/varshitha99999/Scan2Score/tree/digitrec

Automatically reads handwritten roll numbers written in blue ink in the top-right corner of exam/question papers.
"""
import cv2
import numpy as np
import tensorflow as tf
from typing import List, Tuple, Optional
import os

# Configuration parameters (tunable)
TOP_CROP_FRACTION = 0.25    # top 25% of page height (increased from 18%)
RIGHT_CROP_FRACTION = 0.50  # right 50% of page width (increased from 40%)

# Blue ink color range (HSV) - wider range for better detection
BLUE_HSV_LOWER = np.array([80, 30, 30])   # wider range
BLUE_HSV_UPPER = np.array([140, 255, 255])

class DigitRecRollDetector:
    """Roll number detector using the exact digitrec repository approach"""
    
    def __init__(self, model_path: str = "models/digit_recognizer.keras"):
        self.model_path = model_path
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Load the trained CNN model"""
        try:
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
        Recognize roll number from a single paper
        
        Args:
            image_path: Path to the exam paper image
            debug: If True, save debug images
            
        Returns:
            Detected roll number as string, or "NOT_FOUND" if failed
        """
        if self.model is None:
            return "ERROR"
        
        try:
            # Load image
            image = cv2.imread(image_path)
            if image is None:
                print(f"❌ Could not load image: {image_path}")
                return "ERROR"
            
            # Step 1: Crop top-right region
            cropped_region = self._crop_top_right(image)
            if debug:
                cv2.imwrite("debug_1_top_right_crop.jpg", cropped_region)
            
            # Step 2: Create blue ink mask
            blue_mask = self._create_blue_mask(cropped_region)
            if debug:
                cv2.imwrite("debug_2_blue_mask.jpg", blue_mask)
            
            # Step 3: Find digit contours
            digit_boxes = self._find_digit_contours(blue_mask, cropped_region)
            if debug:
                debug_img = cropped_region.copy()
                for x, y, w, h in digit_boxes:
                    cv2.rectangle(debug_img, (x, y), (x+w, y+h), (0, 255, 0), 2)
                cv2.imwrite("debug_3_digit_boxes.jpg", debug_img)
            
            if len(digit_boxes) == 0:
                print("❌ No digit contours found")
                return "NOT_FOUND"
            
            # Step 4: Sort boxes left to right
            digit_boxes = sorted(digit_boxes, key=lambda box: box[0])
            
            # Step 5: Recognize each digit
            roll_digits = []
            confidences = []
            
            for i, (x, y, w, h) in enumerate(digit_boxes):
                # Extract digit region from blue mask
                digit_region = blue_mask[y:y+h, x:x+w]
                
                # Preprocess to MNIST format (28x28 grayscale)
                processed_digit = self._preprocess_digit(digit_region)
                
                # Predict using CNN
                prediction = self.model.predict(processed_digit.reshape(1, 28, 28, 1), verbose=0)
                digit = np.argmax(prediction)
                confidence = np.max(prediction) * 100
                
                roll_digits.append(str(digit))
                confidences.append(confidence)
                
                if debug:
                    print(f"  Digit {i+1}: {digit}  (confidence: {confidence:.1f}%)")
            
            # Step 6: Assemble roll number
            roll_number = ''.join(roll_digits)
            
            if debug:
                print(f"────────────────────────────────────────")
                print(f"  ✅  Roll Number: {roll_number}")
            
            return roll_number
            
        except Exception as e:
            print(f"❌ Error in roll number recognition: {e}")
            return "ERROR"
    
    def _crop_top_right(self, image: np.ndarray) -> np.ndarray:
        """Crop top-right region where roll number is typically written"""
        h, w = image.shape[:2]
        
        # Calculate crop boundaries
        top = 0
        bottom = int(h * TOP_CROP_FRACTION)
        left = int(w * (1 - RIGHT_CROP_FRACTION))
        right = w
        
        return image[top:bottom, left:right]
    
    def _create_blue_mask(self, region: np.ndarray) -> np.ndarray:
        """Create mask to isolate blue ink and filter out printed black text"""
        # Convert to HSV color space
        hsv = cv2.cvtColor(region, cv2.COLOR_BGR2HSV)
        
        # Create mask for blue ink
        mask = cv2.inRange(hsv, BLUE_HSV_LOWER, BLUE_HSV_UPPER)
        
        # Apply morphological operations to clean up the mask
        kernel = np.ones((2, 2), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        
        return mask
    
    def _find_digit_contours(self, mask: np.ndarray, region: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """Find individual digit bounding boxes from the blue mask"""
        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        digit_boxes = []
        
        for contour in contours:
            # Get bounding rectangle
            x, y, w, h = cv2.boundingRect(contour)
            area = cv2.contourArea(contour)
            
            # Filter based on size and aspect ratio (more lenient)
            if (area > 20 and area < 50000 and     # reduced minimum area from 50 to 20
                w > 3 and h > 8 and               # reduced minimum dimensions
                w < 150 and h < 150 and           # increased maximum dimensions
                h/w > 0.3 and h/w < 5.0):         # more lenient aspect ratio
                
                digit_boxes.append((x, y, w, h))
        
        return digit_boxes
    
    def _preprocess_digit(self, digit_region: np.ndarray) -> np.ndarray:
        """Preprocess digit to MNIST format (28x28 grayscale)"""
        # Resize to 28x28
        resized = cv2.resize(digit_region, (28, 28))
        
        # Normalize to 0-1 range
        normalized = resized.astype(np.float32) / 255.0
        
        return normalized
    
    def calibrate(self, image_path: str) -> bool:
        """
        Visual calibration - saves debug images to verify detection pipeline
        Strongly recommended before processing
        """
        print(f"🔧 CALIBRATING with {image_path}")
        
        try:
            # Load image
            image = cv2.imread(image_path)
            if image is None:
                print(f"❌ Could not load image: {image_path}")
                return False
            
            h, w = image.shape[:2]
            
            # 1. Full page with detection zone marked
            full_with_zone = image.copy()
            top = 0
            bottom = int(h * TOP_CROP_FRACTION)
            left = int(w * (1 - RIGHT_CROP_FRACTION))
            right = w
            cv2.rectangle(full_with_zone, (left, top), (right, bottom), (0, 0, 255), 3)
            cv2.imwrite("calib_1_full_page_with_zone.jpg", full_with_zone)
            
            # 2. Cropped region
            cropped = self._crop_top_right(image)
            cv2.imwrite("calib_2_cropped_region.jpg", cropped)
            
            # 3. Blue ink mask
            blue_mask = self._create_blue_mask(cropped)
            cv2.imwrite("calib_3_blue_ink_mask.jpg", blue_mask)
            
            # 4. Detected digits
            digit_boxes = self._find_digit_contours(blue_mask, cropped)
            debug_img = cropped.copy()
            for x, y, w, h in digit_boxes:
                cv2.rectangle(debug_img, (x, y), (x+w, y+h), (0, 255, 0), 2)
            cv2.imwrite("calib_4_detected_digits.jpg", debug_img)
            
            print(f"✅ Calibration complete! Saved 4 debug images:")
            print(f"   calib_1_full_page_with_zone.jpg — red box showing detection zone")
            print(f"   calib_2_cropped_region.jpg — the actual crop")
            print(f"   calib_3_blue_ink_mask.jpg — blue ink isolated")
            print(f"   calib_4_detected_digits.jpg — individual digits boxed in green")
            print(f"   Found {len(digit_boxes)} potential digits")
            
            return True
            
        except Exception as e:
            print(f"❌ Calibration error: {e}")
            return False

def recognize_roll_number_from_image(image_path: str, model_path: str = "models/digit_recognizer.keras", debug: bool = False) -> str:
    """
    Convenience function to recognize roll number from image
    Compatible with existing integration code
    """
    detector = DigitRecRollDetector(model_path)
    return detector.recognize_roll_number(image_path, debug)

if __name__ == "__main__":
    # Test with a sample image
    test_image = "uploads/c-1.jpeg"
    
    if os.path.exists(test_image):
        detector = DigitRecRollDetector()
        
        # First calibrate to see what's happening
        print("🔧 Running calibration...")
        detector.calibrate(test_image)
        
        # Then recognize
        print("\n🔍 Recognizing roll number...")
        result = detector.recognize_roll_number(test_image, debug=True)
        print(f"\n📊 Final Result: {result}")
    else:
        print(f"❌ Test image not found: {test_image}")