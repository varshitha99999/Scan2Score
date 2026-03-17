#!/usr/bin/env python3
"""
Debug marks processing when AI roll detection is enabled
"""
import os
from utils.roll_number_detector import RollNumberDetector
from utils.validation_engine import ValidationEngine
from utils.image_processing import process_image

def debug_ai_marks_processing():
    print("🔍 DEBUGGING AI ROLL DETECTION + MARKS PROCESSING")
    print("=" * 60)
    
    # Initialize components
    try:
        roll_detector = RollNumberDetector("models/digit_recognizer.keras")
        validator = ValidationEngine()
        print("✅ AI components initialized")
    except Exception as e:
        print(f"❌ Failed to initialize AI components: {e}")
        return
    
    # Test with a sample image
    test_image = "uploads/c-1.jpeg"
    
    if not os.path.exists(test_image):
        print(f"❌ Test image not found: {test_image}")
        return
    
    print(f"\n📸 Testing with: {test_image}")
    print("-" * 40)
    
    # Step 1: Roll number detection
    print("🔍 Step 1: Roll Number Detection")
    detection = roll_detector.detect_roll_number(test_image)
    print(f"   Detected: {detection.roll_number}")
    print(f"   Confidence: {detection.confidence:.3f}")
    
    # Step 2: Validation
    print("✅ Step 2: Validation")
    validation = validator.validate_roll_number(
        detection.roll_number, 
        detection.confidence
    )
    print(f"   Valid: {validation.is_valid}")
    if validation.error_messages:
        for error in validation.error_messages:
            print(f"   ⚠️  {error}")
    
    # Step 3: Marks processing (THIS IS THE CRITICAL PART)
    print("🔴 Step 3: Red Ink Marks Processing")
    marks_results = process_image(test_image)
    print(f"   Raw results count: {len(marks_results)}")
    
    # Debug each mark result
    for i, result in enumerate(marks_results):
        print(f"   Mark {i+1}: {result}")
    
    # Step 4: Create marks map (as done in app.py)
    print("📊 Step 4: Marks Map Creation")
    marks_map = {i+1: r['mark'] for i, r in enumerate(marks_results)}
    print(f"   Marks map: {marks_map}")
    print(f"   Total score: {sum(marks_map.values())}/{len(marks_map)}")
    
    # Step 5: Simulate what happens in the upload route
    print("🎯 Step 5: Upload Route Simulation")
    
    if validation.is_valid and detection.roll_number != "NOT_FOUND":
        print("   ✅ Would process automatically:")
        student_data = {
            'roll_no': detection.roll_number,
            'marks_map': marks_map,
            'is_absent': False,
            'detection_confidence': detection.confidence,
            'validation_status': 'auto_detected'
        }
        print(f"   Student data: {student_data}")
    else:
        print("   ⚠️  Would go to manual review:")
        manual_review_data = {
            'image_path': os.path.basename(test_image),
            'detected_roll': detection.roll_number,
            'confidence': detection.confidence,
            'validation_errors': validation.error_messages,
            'suggestions': validation.suggestions,
            'marks_map': marks_map  # THIS IS KEY - marks should be preserved
        }
        print(f"   Manual review data: {manual_review_data}")
        print(f"   📊 Marks ready for manual review: {marks_map}")
    
    print("\n" + "=" * 60)
    print("🎯 DIAGNOSIS:")
    
    if len(marks_results) == 0:
        print("❌ PROBLEM: No marks detected at all!")
        print("   - Check if red ink detection is working")
        print("   - Verify image has red ink corrections")
    elif all(r['mark'] == 0 for r in marks_results):
        print("❌ PROBLEM: All marks classified as 0 (crosses)!")
        print("   - Check classification algorithm")
        print("   - Verify if there are actual ticks in the image")
    elif marks_map:
        print("✅ MARKS PROCESSING: Working correctly")
        print(f"   - Detected {len(marks_results)} marks")
        print(f"   - Score: {sum(marks_map.values())}/{len(marks_map)}")
        print("   - Issue might be in Excel writing or manual review handling")
    else:
        print("❌ PROBLEM: Marks map is empty!")
        print("   - Check marks_map creation logic")

def test_direct_marks_processing():
    """Test marks processing directly without AI components"""
    print("\n🔴 TESTING DIRECT MARKS PROCESSING (NO AI)")
    print("=" * 50)
    
    test_image = "uploads/c-1.jpeg"
    
    if os.path.exists(test_image):
        print(f"📸 Processing: {test_image}")
        
        # Direct processing
        results = process_image(test_image)
        marks_map = {i+1: r['mark'] for i, r in enumerate(results)}
        
        print(f"   Results: {len(results)} marks")
        print(f"   Marks map: {marks_map}")
        print(f"   Score: {sum(marks_map.values())}/{len(marks_map)}")
        
        # Show detailed results
        for i, result in enumerate(results):
            print(f"   Q{i+1}: {result['label']} -> {result['mark']}")
    else:
        print(f"❌ Test image not found: {test_image}")

if __name__ == "__main__":
    debug_ai_marks_processing()
    test_direct_marks_processing()