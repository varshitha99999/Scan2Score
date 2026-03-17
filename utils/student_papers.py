#!/usr/bin/env python3
"""
Student Papers Utility
Functions to retrieve and manage papers for students from uploads folder
"""
import os
import glob
from datetime import datetime
from typing import List, Dict

def get_student_papers(roll_number: str) -> List[Dict]:
    """
    Get all papers for a specific roll number from uploads folder
    
    Args:
        roll_number: The full roll number (e.g., "23WH1A1201") or just the suffix (e.g., "01")
        
    Returns:
        List of dictionaries containing paper information
    """
    uploads_dir = "uploads"
    
    if not os.path.exists(uploads_dir):
        return []
    
    # Extract just the roll number suffix if full roll number is provided
    if roll_number.startswith("23WH1A12"):
        roll_suffix = roll_number.replace("23WH1A12", "")
    else:
        roll_suffix = roll_number
    
    # Get all files in uploads directory
    files = glob.glob(os.path.join(uploads_dir, "*"))
    
    papers = []
    for file_path in files:
        try:
            if os.path.isfile(file_path):
                filename = os.path.basename(file_path)
                
                # Check if this file might belong to the student
                # Look for files that contain the roll number or match naming patterns
                if (roll_suffix in filename.lower() or 
                    filename.lower().startswith(f'cor-{roll_suffix}') or
                    filename.lower().startswith(f'c-{roll_suffix}') or
                    filename.lower() == f'{roll_suffix}.jpg' or
                    filename.lower() == f'{roll_suffix}.jpeg' or
                    filename.lower() == f'{roll_suffix}.png'):
                    
                    # Get file stats
                    stat = os.stat(file_path)
                    modified_time = datetime.fromtimestamp(stat.st_mtime)
                    
                    papers.append({
                        'filename': filename,
                        'filepath': file_path,
                        'timestamp': modified_time,
                        'formatted_date': modified_time.strftime("%B %d, %Y at %I:%M %p"),
                        'size': stat.st_size
                    })
        except Exception as e:
            print(f"Error processing file {file_path}: {e}")
            continue
    
    # Sort by timestamp (newest first)
    papers.sort(key=lambda x: x['timestamp'], reverse=True)
    
    return papers

def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"