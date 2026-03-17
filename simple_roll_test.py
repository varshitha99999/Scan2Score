#!/usr/bin/env python3
"""
Simple Roll Number Detection Test
"""
import os
from utils.roll_number_detector import RollNumberDetector

def simple_test():
    print("🔍 SIMPLE ROLL NUMBER DETECTION TEST")
    
    # Test image
    test_image = "uploads/c-1.jpeg"
    
    if not os.path.exists(test_image):
        print(f"❌ Test image not found: {test_image}")
        return
    
    try:
        # Initialize detector
        detector = RollNumberDetector("models/digit_recognizer.keras")
        print("✅ Detector initialized")
        
        # Test detection
        result = detector.detect_roll_number(test_image)
        
        print(f"📊 Results:")
        print(f"   Roll Number: {result.roll_number}")
        print(f"   Confidence: {result.confidence:.3f}")
        print(f"   Debug Info: {result.debug_info}")
        
        if result.roll_number == "NOT_FOUND":
            print("\n🔍 Analyzing why detection failed:")
            debug = result.debug_info
            
            if 'blue_pixels' in debug:
                print(f"   Blue pixels found: {debug['blue_pixels']}")
                if debug['blue_pixels'] == 0:
                    print("   ❌ No blue pixels detected - check HSV range")
            
            if 'digit_boxes' in debug:
                print(f"   Digit boxes found: {debug['digit_boxes']}")
                if debug['digit_boxes'] == 0:
                    print("   ❌ No digit contours found - check area thresholds")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    simple_test()