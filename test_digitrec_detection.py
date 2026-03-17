#!/usr/bin/env python3
"""
Test the digitrec-based roll number detection
"""
import os
from utils.digitrec_roll_detector import DigitRecRollDetector

def test_digitrec_detection():
    print("🧪 TESTING DIGITREC ROLL NUMBER DETECTION")
    print("=" * 50)
    
    # Test images
    test_images = [
        "uploads/c-1.jpeg",
        "uploads/c-2.jpeg"
    ]
    
    # Initialize detector
    detector = DigitRecRollDetector("models/digit_recognizer.keras")
    
    for image_path in test_images:
        if not os.path.exists(image_path):
            print(f"❌ Image not found: {image_path}")
            continue
        
        print(f"\n📄 Testing: {os.path.basename(image_path)}")
        print("-" * 30)
        
        # Run calibration first
        print("🔧 Calibration:")
        detector.calibrate(image_path)
        
        # Then detect roll number
        print("\n🔍 Detection:")
        roll_number = detector.recognize_roll_number(image_path, debug=True)
        
        print(f"\n📊 Result: {roll_number}")
        
        if roll_number not in ["NOT_FOUND", "ERROR"]:
            print(f"✅ Successfully detected roll number: {roll_number}")
        else:
            print(f"❌ Detection failed: {roll_number}")

if __name__ == "__main__":
    test_digitrec_detection()