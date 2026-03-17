#!/usr/bin/env python3
"""
Test Student Authentication System
"""
import os
from utils.student_papers import get_student_papers, format_file_size

def test_student_auth():
    print("🧪 TESTING NEW STUDENT AUTHENTICATION SYSTEM")
    print("=" * 60)
    
    # Test authentication logic
    print("\n🔐 Testing Authentication Logic:")
    
    test_cases = [
        {"email": "01@scan.com", "password": "01", "should_work": True},
        {"email": "02@scan.com", "password": "02", "should_work": True},
        {"email": "123@scan.com", "password": "123", "should_work": True},
        {"email": "01@scan.com", "password": "02", "should_work": False},
        {"email": "invalid@email.com", "password": "01", "should_work": False},
    ]
    
    for case in test_cases:
        email = case["email"]
        password = case["password"]
        expected = case["should_work"]
        
        # Simulate authentication logic
        if email.endswith('@scan.com'):
            roll_number = email.replace('@scan.com', '')
            auth_success = (password == roll_number)
        else:
            auth_success = False
        
        status = "✅ PASS" if auth_success == expected else "❌ FAIL"
        print(f"   {status} {email} / {password} → Expected: {expected}, Got: {auth_success}")
    
    # Test paper retrieval from uploads folder
    print(f"\n📁 Testing Paper Retrieval from Uploads:")
    
    uploads_dir = "uploads"
    if os.path.exists(uploads_dir):
        files = os.listdir(uploads_dir)
        print(f"   Files in uploads: {len(files)}")
        for file in files[:5]:  # Show first 5 files
            print(f"   - {file}")
        if len(files) > 5:
            print(f"   ... and {len(files) - 5} more files")
    else:
        print(f"   ❌ Uploads directory not found")
    
    # Test specific roll numbers
    test_rolls = ["01", "02", "1", "2"]
    
    for roll in test_rolls:
        papers = get_student_papers(roll)
        print(f"\n📄 Roll {roll}: Found {len(papers)} paper(s)")
        for paper in papers:
            size_str = format_file_size(paper['size'])
            print(f"   - {paper['filename']} ({size_str})")

if __name__ == "__main__":
    test_student_auth()