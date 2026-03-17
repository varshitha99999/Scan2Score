#!/usr/bin/env python3
"""
Test Student Portal Functionality
"""
import os
from utils.student_papers import get_student_papers, format_file_size

def test_student_portal():
    print("🧪 TESTING STUDENT PORTAL FUNCTIONALITY")
    print("=" * 50)
    
    # Test roll numbers
    test_rolls = ["23WH1A1201", "23WH1A1202", "23WH1A1203"]
    
    for roll in test_rolls:
        print(f"\n📄 Testing roll number: {roll}")
        papers = get_student_papers(roll)
        
        if papers:
            print(f"   ✅ Found {len(papers)} paper(s):")
            for i, paper in enumerate(papers, 1):
                size_str = format_file_size(paper['size'])
                print(f"      {i}. {paper['filename']}")
                print(f"         Date: {paper['formatted_date']}")
                print(f"         Size: {size_str}")
        else:
            print(f"   📭 No papers found for {roll}")
    
    # Test processed_papers directory
    print(f"\n📁 Processed Papers Directory:")
    processed_dir = "processed_papers"
    if os.path.exists(processed_dir):
        files = os.listdir(processed_dir)
        print(f"   Total files: {len(files)}")
        for file in files:
            file_path = os.path.join(processed_dir, file)
            size = os.path.getsize(file_path)
            print(f"   - {file} ({format_file_size(size)})")
    else:
        print(f"   ❌ Directory not found: {processed_dir}")

if __name__ == "__main__":
    test_student_portal()