"""
Roll Number Detector using CNN Model
====================================
Integrates the existing CNN-based digit recognition system from the digitrec branch
to detect handwritten roll numbers from answer sheet images.

This module provides a unified interface for roll number detection that integrates
with the existing paper correction workflow.
"""

import os
import sys
import cv2
import numpy as np
from PIL import Image, ImageFilter
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass
import time

# Suppress TensorFlow warnings
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"
import tensorflow as tf


@dataclass
class DetectionResult:
    """Result of roll number detection"""
    roll_number: str
    confidence: float
    bounding_box: Tuple[int, int, int, int]  # (x, y, width, height)
    processing_time: float
    model_used: str
    digit_confidences: List[float]
    debug_info: Dict[str, Any]


class RollNumberDetector:
    """
    CNN-based roll number detector that extracts handwritten roll numbers
    from answer sheet images using the trained digit recognition model.
    """
    
    def __init__(self, model_path: str = "models/digit_recognizer.keras", config: Dict = None):
        """
        Initialize the roll number detector.
        
        Args:
            model_path: Path to the trained CNN model
            config: Configuration dictionary for detection parameters
        """
        self.model_path = model_path
        self.config = config or self._default_config()
        self.model = None
        self._load_model()
    
    def _default_config(self) -> Dict:
        """Default configuration for roll number detection"""
        return {
            # Cropping parameters for roll number region
            'top_crop_fraction': 0.18,      # top 18% of page height
            'right_crop_fraction': 0.40,    # right 40% of page width
            
            # HSV range for blue ink detection
            'blue_hsv_lower': [90, 50, 50],
            'blue_hsv_upper': [135, 255, 255],
            
            # Digit filtering parameters
            'min_digit_area': 80,
            'max_digit_area': 50000,
            'min_confidence': 0.7,
            
            # Processing parameters
            'merge_gap_threshold': 3,
            'aspect_ratio_filter': 2.5,
            'debug_mode': False
        }
    
    def _load_model(self):
        """Load the trained CNN model"""
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Model not found at '{self.model_path}'. Please ensure the model file exists.")
        
        try:
            self.model = tf.keras.models.load_model(self.model_path)
            print(f"✅ Loaded CNN model from {self.model_path}")
        except Exception as e:
            raise RuntimeError(f"Failed to load model: {str(e)}")
    
    def detect_roll_number(self, image_path: str, roi: Optional[Tuple] = None) -> DetectionResult:
        """
        Detect roll number from a single image.
        
        Args:
            image_path: Path to the answer sheet image
            roi: Optional region of interest (x, y, width, height)
            
        Returns:
            DetectionResult with detected roll number and metadata
        """
        start_time = time.time()
        debug_info = {}
        
        try:
            # Load image
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError(f"Cannot read image at '{image_path}'")
            
            debug_info['original_shape'] = image.shape
            
            # Step 1: Crop top-right region (roll number area)
            region = self._crop_top_right(image)
            debug_info['cropped_shape'] = region.shape
            
            # Step 2: Isolate blue ink
            mask = self._isolate_blue_ink(region)
            debug_info['blue_pixels'] = np.count_nonzero(mask)
            
            # Step 3: Find digit contours
            boxes = self._find_digit_contours(mask, region)
            debug_info['digit_boxes'] = len(boxes)
            
            if not boxes:
                return DetectionResult(
                    roll_number="NOT_FOUND",
                    confidence=0.0,
                    bounding_box=(0, 0, 0, 0),
                    processing_time=time.time() - start_time,
                    model_used="cnn_digit_recognizer",
                    digit_confidences=[],
                    debug_info=debug_info
                )
            
            # Step 4: Recognize each digit
            roll_number = ""
            digit_confidences = []
            
            for box in boxes:
                digit_array = self._preprocess_digit(mask, box)
                probs = self.model.predict(digit_array, verbose=0)[0]
                digit = int(np.argmax(probs))
                confidence = float(probs[digit])
                
                roll_number += str(digit)
                digit_confidences.append(confidence)
            
            # Calculate overall confidence (average of digit confidences)
            overall_confidence = np.mean(digit_confidences) if digit_confidences else 0.0
            
            # Get combined bounding box
            combined_bbox = self._get_combined_bbox(boxes)
            
            processing_time = time.time() - start_time
            
            return DetectionResult(
                roll_number=roll_number,
                confidence=overall_confidence,
                bounding_box=combined_bbox,
                processing_time=processing_time,
                model_used="cnn_digit_recognizer",
                digit_confidences=digit_confidences,
                debug_info=debug_info
            )
            
        except Exception as e:
            return DetectionResult(
                roll_number="ERROR",
                confidence=0.0,
                bounding_box=(0, 0, 0, 0),
                processing_time=time.time() - start_time,
                model_used="cnn_digit_recognizer",
                digit_confidences=[],
                debug_info={'error': str(e)}
            )
    
    def batch_detect(self, image_paths: List[str]) -> List[DetectionResult]:
        """
        Process multiple images in batch.
        
        Args:
            image_paths: List of paths to answer sheet images
            
        Returns:
            List of DetectionResult objects
        """
        results = []
        for image_path in image_paths:
            result = self.detect_roll_number(image_path)
            results.append(result)
        return results
    
    def _crop_top_right(self, image: np.ndarray) -> np.ndarray:
        """Crop the top-right region where roll numbers are typically written"""
        h, w = image.shape[:2]
        top = 0
        bottom = int(h * self.config['top_crop_fraction'])
        left = int(w * (1 - self.config['right_crop_fraction']))
        right = w
        
        region = image[top:bottom, left:right]
        
        if self.config['debug_mode']:
            cv2.imwrite("debug_1_top_right_crop.jpg", region)
        
        return region
    
    def _isolate_blue_ink(self, region: np.ndarray) -> np.ndarray:
        """Isolate blue ink pixels using HSV color masking"""
        hsv = cv2.cvtColor(region, cv2.COLOR_BGR2HSV)
        
        lower = np.array(self.config['blue_hsv_lower'])
        upper = np.array(self.config['blue_hsv_upper'])
        mask = cv2.inRange(hsv, lower, upper)
        
        # Morphological operations to clean up the mask
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=1)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
        
        if self.config['debug_mode']:
            cv2.imwrite("debug_2_blue_mask.jpg", mask)
        
        return mask
    
    def _find_digit_contours(self, mask: np.ndarray, region: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """Find bounding boxes of individual digits"""
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        boxes = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if not (self.config['min_digit_area'] < area < self.config['max_digit_area']):
                continue
                
            x, y, w, h = cv2.boundingRect(cnt)
            aspect = w / float(h) if h > 0 else 0
            
            # Filter out thin lines (not digits)
            if aspect > self.config['aspect_ratio_filter']:
                continue
                
            boxes.append((x, y, w, h))
        
        # Merge boxes that are very close horizontally
        boxes = self._merge_close_boxes(boxes)
        
        # Sort left to right
        boxes.sort(key=lambda b: b[0])
        
        if self.config['debug_mode']:
            vis = region.copy()
            for i, (x, y, w, h) in enumerate(boxes):
                cv2.rectangle(vis, (x, y), (x+w, y+h), (0, 255, 0), 2)
                cv2.putText(vis, str(i), (x, y-5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,0), 2)
            cv2.imwrite("debug_3_digit_boxes.jpg", vis)
        
        return boxes
    
    def _merge_close_boxes(self, boxes: List[Tuple[int, int, int, int]]) -> List[Tuple[int, int, int, int]]:
        """Merge horizontally adjacent bounding boxes"""
        if not boxes:
            return boxes
            
        boxes = sorted(boxes, key=lambda b: b[0])
        merged = [boxes[0]]
        
        for x, y, w, h in boxes[1:]:
            px, py, pw, ph = merged[-1]
            if x - (px + pw) < self.config['merge_gap_threshold']:
                # Merge boxes
                nx = min(px, x)
                ny = min(py, y)
                nw = max(px+pw, x+w) - nx
                nh = max(py+ph, y+h) - ny
                merged[-1] = (nx, ny, nw, nh)
            else:
                merged.append((x, y, w, h))
        
        return merged
    
    def _preprocess_digit(self, mask: np.ndarray, box: Tuple[int, int, int, int]) -> np.ndarray:
        """Preprocess a single digit for CNN prediction"""
        x, y, w, h = box
        pad = 6
        x1 = max(0, x - pad)
        y1 = max(0, y - pad)
        x2 = min(mask.shape[1], x + w + pad)
        y2 = min(mask.shape[0], y + h + pad)
        
        digit_mask = mask[y1:y2, x1:x2]
        
        # Convert to PIL for better resizing
        pil = Image.fromarray(digit_mask)
        pil.thumbnail((20, 20), Image.LANCZOS)
        
        # Create 28x28 canvas (MNIST style)
        canvas = Image.new("L", (28, 28), 0)
        xo = (28 - pil.width) // 2
        yo = (28 - pil.height) // 2
        canvas.paste(pil, (xo, yo))
        canvas = canvas.filter(ImageFilter.GaussianBlur(0.5))
        
        # Convert to numpy array for model
        arr = np.array(canvas, dtype="float32") / 255.0
        return arr.reshape(1, 28, 28, 1)
    
    def _get_combined_bbox(self, boxes: List[Tuple[int, int, int, int]]) -> Tuple[int, int, int, int]:
        """Get combined bounding box for all digits"""
        if not boxes:
            return (0, 0, 0, 0)
        
        min_x = min(box[0] for box in boxes)
        min_y = min(box[1] for box in boxes)
        max_x = max(box[0] + box[2] for box in boxes)
        max_y = max(box[1] + box[3] for box in boxes)
        
        return (min_x, min_y, max_x - min_x, max_y - min_y)
    
    def get_model_info(self) -> Dict[str, Any]:
        """Return model metadata and information"""
        if self.model is None:
            return {"error": "Model not loaded"}
        
        return {
            "model_path": self.model_path,
            "model_type": "CNN Digit Recognizer",
            "input_shape": self.model.input_shape,
            "output_shape": self.model.output_shape,
            "total_params": self.model.count_params(),
            "config": self.config
        }


def recognize_roll_number_from_image(image_path: str, model_path: str = "models/digit_recognizer.keras", debug: bool = False) -> str:
    """
    Convenience function to recognize roll number from a single image.
    Compatible with the original recognize_roll.py interface.
    
    Args:
        image_path: Path to the answer sheet image
        model_path: Path to the trained model
        debug: Whether to save debug images
        
    Returns:
        Detected roll number as string
    """
    config = {
        'debug_mode': debug
    }
    
    detector = RollNumberDetector(model_path, config)
    result = detector.detect_roll_number(image_path)
    
    if debug:
        print(f"Detected roll number: {result.roll_number}")
        print(f"Confidence: {result.confidence:.3f}")
        print(f"Processing time: {result.processing_time:.3f}s")
        print(f"Debug info: {result.debug_info}")
    
    return result.roll_number