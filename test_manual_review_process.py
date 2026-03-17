#!/usr/bin/env python3
"""
Test the complete manual review process to identify where marks are getting lost
"""
import json
from utils.image_processing import process_image

def test_manual_review_process():
    print("🔍 TESTING COMPLETE MANUAL REVIEW PROCESS")
    print("=" * 60)
    
    # Step 1: Simulate marks processing (as done in upload route)
    test_image = "uploads/c-1.jpeg"
    print(f"📸 Step 1: Processing {test_image}")
    
    marks_results = process_image(test_image)
    marks_map = {i+1: r['mark'] for i, r in enumerate(marks_results)}
    
    print(f"   Marks results: {len(marks_results)} marks")
    print(f"   Marks map: {marks_map}")
    print(f"   Total score: {sum(marks_map.values())}/{len(marks_map)}")
    
    # Step 2: Simulate manual review data creation (as done in upload route)
    print("\n📋 Step 2: Creating manual review data")
    
    manual_review_data = {
        'image_path': 'c-1.jpeg',
        'detected_roll': 'NOT_FOUND',
        'confidence': 0.0,
        'validation_errors': ['Roll number not detected'],
        'suggestions': ['Check image quality and blue ink visibility'],
        'marks_map': marks_map
    }
    
    print(f"   Manual review data: {manual_review_data}")
    
    # Step 3: Simulate template JSON conversion (as done in template)
    print("\n🌐 Step 3: Template JSON conversion")
    
    marks_data_json = json.dumps(marks_map)
    print(f"   JSON string: {marks_data_json}")
    
    # Step 4: Simulate form submission parsing (as done in manual_review_submit)
    print("\n📝 Step 4: Form submission parsing (FIXED)")
    
    try:
        marks_map_raw = json.loads(marks_data_json)
        # NEW: Convert string keys to integers for Excel processing
        parsed_marks_map = {}
        for key, value in marks_map_raw.items():
            try:
                parsed_marks_map[int(key)] = int(value)
            except (ValueError, TypeError):
                continue
        print(f"   Raw parsed (string keys): {marks_map_raw}")
        print(f"   Fixed parsed (int keys): {parsed_marks_map}")
        print(f"   Fixed total score: {sum(parsed_marks_map.values())}/{len(parsed_marks_map)}")
    except Exception as e:
        print(f"   ❌ JSON parsing error: {e}")
        parsed_marks_map = {}
    
    # Step 5: Simulate student data creation (as done in manual_review_submit)
    print("\n👨‍🎓 Step 5: Student data creation")
    
    corrected_roll = "23WH1A1253"  # Simulated user input
    
    student_data = {
        'roll_no': corrected_roll.upper(),
        'marks_map': parsed_marks_map,
        'is_absent': False,
        'detection_confidence': 1.0,
        'validation_status': 'manually_corrected'
    }
    
    print(f"   Student data: {student_data}")
    print(f"   Final marks: {student_data['marks_map']}")
    print(f"   Final score: {sum(student_data['marks_map'].values()) if student_data['marks_map'] else 0}")
    
    # Step 6: Check if marks are preserved through the entire process
    print("\n🎯 Step 6: Process integrity check")
    
    original_score = sum(marks_map.values())
    final_score = sum(student_data['marks_map'].values()) if student_data['marks_map'] else 0
    
    if original_score == final_score:
        print(f"   ✅ SUCCESS: Marks preserved through entire process")
        print(f"   Original: {original_score}, Final: {final_score}")
    else:
        print(f"   ❌ FAILURE: Marks lost in process")
        print(f"   Original: {original_score}, Final: {final_score}")
        print(f"   Original map: {marks_map}")
        print(f"   Final map: {student_data['marks_map']}")
    
    return student_data

def test_excel_writing_simulation():
    """Test if the issue is in Excel writing"""
    print("\n📊 TESTING EXCEL WRITING SIMULATION")
    print("=" * 40)
    
    # Simulate student data with marks
    student_data = [{
        'roll_no': '23WH1A1253',
        'marks_map': {1: 1, 2: 1, 3: 0, 4: 0, 5: 1, 6: 0, 7: 1, 8: 1, 9: 1, 10: 0},
        'is_absent': False,
        'detection_confidence': 1.0,
        'validation_status': 'manually_corrected'
    }]
    
    print(f"Student data for Excel: {student_data}")
    
    # Check the marks_map structure
    for student in student_data:
        print(f"Roll: {student['roll_no']}")
        print(f"Marks map: {student['marks_map']}")
        print(f"Total marks: {sum(student['marks_map'].values())}")
        
        # Simulate what update_excel_com_batch expects
        for q_num in range(1, 21):  # Questions 1-20
            mark = int(student['marks_map'].get(q_num, 0))
            print(f"   Q{q_num:2d}: {mark}")

if __name__ == "__main__":
    student_data = test_manual_review_process()
    test_excel_writing_simulation()