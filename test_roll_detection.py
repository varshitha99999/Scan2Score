"""
Test script for roll number detection functionality
"""
import os
import sys
from utils.roll_number_detector import RollNumberDetector, recognize_roll_number_from_image
from utils.validation_engine import ValidationEngine
from utils.excel_matcher import ExcelMatcher

def test_roll_detection():
    """Test the roll number detection system"""
    print("🧪 Testing Roll Number Detection System")
    print("=" * 50)
    
    # Check if model exists
    model_path = "models/digit_recognizer.keras"
    if not os.path.exists(model_path):
        print(f"❌ Model not found at {model_path}")
        print("Please run: python download_model.py")
        return False
    
    print(f"✅ Model found at {model_path}")
    
    # Test 1: Initialize detector
    try:
        detector = RollNumberDetector(model_path)
        print("✅ Roll number detector initialized successfully")
        
        # Print model info
        model_info = detector.get_model_info()
        print(f"📊 Model info: {model_info['model_type']}")
        print(f"📊 Total parameters: {model_info['total_params']:,}")
        
    except Exception as e:
        print(f"❌ Failed to initialize detector: {e}")
        return False
    
    # Test 2: Initialize validation engine
    try:
        validator = ValidationEngine()
        print("✅ Validation engine initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize validator: {e}")
        return False
    
    # Test 3: Test validation with sample roll numbers
    test_rolls = [
        ("23WH1A1253", 0.95),
        ("24CS1A0501", 0.88),
        ("INVALID123", 0.75),
        ("", 0.0),
        ("23WH1A", 0.85)  # Too short
    ]
    
    print("\n🔍 Testing validation engine:")
    for roll, confidence in test_rolls:
        result = validator.validate_roll_number(roll, confidence)
        status = "✅ VALID" if result.is_valid else "❌ INVALID"
        print(f"  {roll:<12} (conf: {confidence:.2f}) → {status}")
        if result.error_messages:
            for error in result.error_messages:
                print(f"    ⚠️  {error}")
    
    # Test 4: Test Excel matcher (if master template exists)
    excel_path = "master_template.xlsx"
    if os.path.exists(excel_path):
        try:
            matcher = ExcelMatcher(excel_path)
            print(f"✅ Excel matcher initialized with {excel_path}")
            
            existing_rolls = matcher.get_existing_roll_numbers()
            print(f"📊 Found {len(existing_rolls)} existing roll numbers in Excel")
            
            # Test matching
            if existing_rolls:
                test_roll = existing_rolls[0] if existing_rolls else "23WH1A1253"
                match_result = matcher.find_student_record(test_roll)
                print(f"🔍 Test match for '{test_roll}': {'✅ FOUND' if match_result.match_found else '❌ NOT FOUND'}")
            
        except Exception as e:
            print(f"⚠️  Excel matcher test failed: {e}")
    else:
        print(f"⚠️  Excel template not found at {excel_path}")
    
    # Test 5: Test with sample image (if available)
    test_images = [
        "test_marks.jpg",
        "input/RedInkDetection.jpg",
        "uploads/Screenshot_2026-01-22_191515.png"
    ]
    
    test_image = None
    for img_path in test_images:
        if os.path.exists(img_path):
            test_image = img_path
            break
    
    if test_image:
        print(f"\n📸 Testing with sample image: {test_image}")
        try:
            result = detector.detect_roll_number(test_image)
            print(f"🔍 Detected roll number: {result.roll_number}")
            print(f"📊 Confidence: {result.confidence:.3f}")
            print(f"⏱️  Processing time: {result.processing_time:.3f}s")
            print(f"🤖 Model used: {result.model_used}")
            
            if result.debug_info:
                print(f"🔧 Debug info: {result.debug_info}")
                
        except Exception as e:
            print(f"❌ Image processing failed: {e}")
    else:
        print("⚠️  No test images found for detection test")
    
    print("\n" + "=" * 50)
    print("🎉 Roll number detection system test completed!")
    print("\n💡 To test with your own images:")
    print("   1. Place answer sheet images in the uploads/ folder")
    print("   2. Go to http://127.0.0.1:5000")
    print("   3. Login as teacher (teacher@college.com / teacher123)")
    print("   4. Go to Paper Correction")
    print("   5. Check 'Enable AI Roll Number Detection'")
    print("   6. Upload your images and test!")
    
    return True

if __name__ == "__main__":
    test_roll_detection()