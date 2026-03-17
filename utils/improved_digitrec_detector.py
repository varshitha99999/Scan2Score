#!/usr/bin/env python3
"""
Improved DigitRec Roll Number Detector
Enhanced to handle thin digits like "1" and different handwriting styles
"""
import cv2
import numpy as np
import tensorflow as tf
from typing import List, Tuple, Optional
import os

class ImprovedDigitRecDetector:
    """Enhanced roll number detector that handles thin digits better"""
    
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
        Enhanced roll number recognition with multiple strategies
        """
        if self.model is None:
            return "ERROR"
        
        try:
            # Load image
            image = cv2.imread(image_path)
            if image is None:
                print(f"❌ Could not load image: {image_path}")
                return "ERROR"
            
            # Try multiple detection strategies
            strategies = [
                {"name": "Top-Right Large", "top": 0.25, "right": 0.50, "hsv_lower": [80, 30, 30], "hsv_upper": [140, 255, 255]},
                {"name": "Top-Right Medium", "top": 0.18, "right": 0.40, "hsv_lower": [90, 50, 50], "hsv_upper": [135, 255, 255]},
                {"name": "Top-Right Small", "top": 0.15, "right": 0.35, "hsv_lower": [85, 40, 40], "hsv_upper": [130, 255, 255]},
                {"name": "Top-Center", "top": 0.20, "right": 0.70, "hsv_lower": [80, 30, 30], "hsv_upper": [140, 255, 255]},
                {"name": "Very Lenient", "top": 0.30, "right": 0.60, "hsv_lower": [70, 20, 20], "hsv_upper": [150, 255, 255]}
            ]
            
            best_result = None
            best_confidence = 0
            
            for strategy in strategies:
                if debug:
                    print(f"\n🧪 Trying strategy: {strategy['name']}")
                
                result = self._try_detection_strategy(image, strategy, debug)
                
                if result and result['roll_number'] not in ["NOT_FOUND", "ERROR"]:
                    avg_confidence = np.mean(result['confidences']) if result['confidences'] else 0
                    
                    if debug:
                        print(f"   Result: {result['roll_number']} (avg confidence: {avg_confidence:.1f}%)")
                    
                    # Prefer results with 2+ digits and good confidence
                    if len(result['roll_number']) >= 2 and avg_confidence > best_confidence:
                        best_result = result
                        best_confidence = avg_confidence
                    elif best_result is None:  # Take any result if we have none
                        best_result = result
                        best_confidence = avg_confidence
            
            if best_result:
                if debug:
                    print(f"\n✅ Best result: {best_result['roll_number']} (confidence: {best_confidence:.1f}%)")
                return best_result['roll_number']
            else:
                if debug:
                    print(f"\n❌ No valid roll number found with any strategy")
                return "NOT_FOUND"
                
        except Exception as e:
            print(f"❌ Error in roll number recognition: {e}")
            return "ERROR"
    
    def _try_detection_strategy(self, image: np.ndarray, strategy: dict, debug: bool = False) -> Optional[dict]:
        """Try a specific detection strategy"""
        try:
            # Step 1: Crop region
            cropped_region = self._crop_region(image, strategy['top'], strategy['right'])
            
            # Step 2: Create blue ink mask
            blue_mask = self._create_blue_mask(cropped_region, strategy['hsv_lower'], strategy['hsv_upper'])
            
            # Step 3: Find digit contours with enhanced detection
            digit_boxes = self._find_digit_contours_enhanced(blue_mask, cropped_region)
            
            if len(digit_boxes) == 0:
                return None
            
            # Step 4: Sort boxes left to right
            digit_boxes = sorted(digit_boxes, key=lambda box: box[0])
            
            # Step 5: Recognize each digit
            roll_digits = []
            confidences = []
            
            for i, (x, y, w, h) in enumerate(digit_boxes):
                # Extract digit region from blue mask
                digit_region = blue_mask[y:y+h, x:x+w]
                
                # Preprocess to MNIST format
                processed_digit = self._preprocess_digit(digit_region)
                
                # Predict using CNN
                prediction = self.model.predict(processed_digit.reshape(1, 28, 28, 1), verbose=0)
                digit = np.argmax(prediction)
                confidence = np.max(prediction) * 100
                
                roll_digits.append(str(digit))
                confidences.append(confidence)
                
                if debug:
                    print(f"     Digit {i+1}: {digit} (confidence: {confidence:.1f}%)")
            
            # Step 6: Assemble roll number
            roll_number = ''.join(roll_digits)
            
            return {
                'roll_number': roll_number,
                'confidences': confidences,
                'digit_count': len(digit_boxes)
            }
            
        except Exception as e:
            if debug:
                print(f"     Strategy failed: {e}")
            return None
    
    def _crop_region(self, image: np.ndarray, top_fraction: float, right_fraction: float) -> np.ndarray:
        """Crop region based on fractions"""
        h, w = image.shape[:2]
        
        top = 0
        bottom = int(h * top_fraction)
        left = int(w * (1 - right_fraction))
        right = w
        
        return image[top:bottom, left:right]
    
    def _create_blue_mask(self, region: np.ndarray, hsv_lower: list, hsv_upper: list) -> np.ndarray:
        """Create mask to isolate blue ink"""
        # Convert to HSV color space
        hsv = cv2.cvtColor(region, cv2.COLOR_BGR2HSV)
        
        # Create mask for blue ink
        mask = cv2.inRange(hsv, np.array(hsv_lower), np.array(hsv_upper))
        
        # Apply morphological operations to clean up the mask
        kernel = np.ones((2, 2), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        
        return mask
    
    def _find_digit_contours_enhanced(self, mask: np.ndarray, region: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """Enhanced digit contour detection that handles thin digits better"""
        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        digit_boxes = []
        
        for contour in contours:
            # Get bounding rectangle
            x, y, w, h = cv2.boundingRect(contour)
            area = cv2.contourArea(contour)
            
            # Very lenient filtering to catch thin digits like "1"
            if (area > 10 and area < 50000 and      # very low minimum area
                w > 2 and h > 5 and                # very small minimum dimensions
                w < 200 and h < 200 and            # large maximum dimensions
                h > w * 0.8):                      # height should be at least 80% of width (catches thin "1")
                
                digit_boxes.append((x, y, w, h))
        
        # If we found very few contours, try with even more lenient parameters
        if len(digit_boxes) < 2:
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                area = cv2.contourArea(contour)
                
                # Extremely lenient for catching missed digits
                if (area > 5 and area < 50000 and
                    w > 1 and h > 3 and
                    w < 250 and h < 250):
                    
                    # Avoid duplicates
                    is_duplicate = False
                    for existing_x, existing_y, existing_w, existing_h in digit_boxes:
                        if abs(x - existing_x) < 10 and abs(y - existing_y) < 10:
                            is_duplicate = True
                            break
                    
                    if not is_duplicate:
                        digit_boxes.append((x, y, w, h))
        
        return digit_boxes
    
    def _preprocess_digit(self, digit_region: np.ndarray) -> np.ndarray:
        """Preprocess digit to MNIST format (28x28 grayscale)"""
        # Resize to 28x28
        resized = cv2.resize(digit_region, (28, 28))
        
        # Normalize to 0-1 range
        normalized = resized.astype(np.float32) / 255.0
        
        return normalized
    
    def calibrate_enhanced(self, image_path: str) -> bool:
        """Enhanced calibration that shows all strategies"""
        print(f"🔧 ENHANCED CALIBRATION with {image_path}")
        
        try:
            image = cv2.imread(image_path)
            if image is None:
                print(f"❌ Could not load image: {image_path}")
                return False
            
            strategies = [
                {"name": "Top-Right Large", "top": 0.25, "right": 0.50, "hsv_lower": [80, 30, 30], "hsv_upper": [140, 255, 255]},
                {"name": "Top-Right Medium", "top": 0.18, "right": 0.40, "hsv_lower": [90, 50, 50], "hsv_upper": [135, 255, 255]},
                {"name": "Top-Center", "top": 0.20, "right": 0.70, "hsv_lower": [80, 30, 30], "hsv_upper": [140, 255, 255]}
            ]
            
            for i, strategy in enumerate(strategies):
                print(f"\n📍 Strategy {i+1}: {strategy['name']}")
                
                # Crop region
                cropped = self._crop_region(image, strategy['top'], strategy['right'])
                cv2.imwrite(f"enhanced_calib_{i+1}_crop_{strategy['name'].replace(' ', '_').lower()}.jpg", cropped)
                
                # Blue mask
                blue_mask = self._create_blue_mask(cropped, strategy['hsv_lower'], strategy['hsv_upper'])
                cv2.imwrite(f"enhanced_calib_{i+1}_mask_{strategy['name'].replace(' ', '_').lower()}.jpg", blue_mask)
                
                # Digit detection
                digit_boxes = self._find_digit_contours_enhanced(blue_mask, cropped)
                debug_img = cropped.copy()
                for x, y, w, h in digit_boxes:
                    cv2.rectangle(debug_img, (x, y), (x+w, y+h), (0, 255, 0), 2)
                cv2.imwrite(f"enhanced_calib_{i+1}_digits_{strategy['name'].replace(' ', '_').lower()}.jpg", debug_img)
                
                print(f"   Found {len(digit_boxes)} potential digits")
            
            print(f"\n✅ Enhanced calibration complete! Check enhanced_calib_*.jpg files")
            return True
            
        except Exception as e:
            print(f"❌ Enhanced calibration error: {e}")
            return False

def test_improved_detection():
    """Test the improved detection"""
    print("🧪 TESTING IMPROVED DIGITREC DETECTION")
    print("=" * 50)
    
    test_images = ["uploads/cor-01.png", "uploads/c-1.jpeg", "uploads/c-2.jpeg"]
    
    detector = ImprovedDigitRecDetector()
    
    for image_path in test_images:
        if not os.path.exists(image_path):
            print(f"❌ Image not found: {image_path}")
            continue
        
        print(f"\n📄 Testing: {os.path.basename(image_path)}")
        print("-" * 40)
        
        # Enhanced calibration
        detector.calibrate_enhanced(image_path)
        
        # Detection
        result = detector.recognize_roll_number(image_path, debug=True)
        print(f"\n🎯 FINAL RESULT: {result}")

if __name__ == "__main__":
    test_improved_detection()