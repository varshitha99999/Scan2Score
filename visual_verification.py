#!/usr/bin/env python3
"""
Visual verification tool to show detected marks with their classifications
"""
import cv2
import numpy as np
import os
from utils.image_processing import get_contours, classify_mark

def create_visual_verification(image_path):
    """Create a visual verification image showing detected marks and classifications"""
    print(f"🎨 Creating visual verification for: {image_path}")
    
    # Get contours and image
    contours, img = get_contours(image_path)
    
    if contours is None or len(contours) == 0:
        print("❌ No contours found!")
        return
    
    # Create visualization
    vis_img = img.copy()
    
    # Colors for different classifications
    tick_color = (0, 255, 0)    # Green for ticks (correct)
    cross_color = (0, 0, 255)   # Red for crosses (wrong)
    
    tick_count = 0
    cross_count = 0
    
    print(f"📊 Processing {len(contours)} detected marks:")
    
    for i, cnt in enumerate(contours):
        # Classify the mark
        mark, label = classify_mark(cnt, img)
        
        # Choose color based on classification
        color = tick_color if label == "Tick" else cross_color
        
        # Draw contour
        cv2.drawContours(vis_img, [cnt], -1, color, 3)
        
        # Get bounding box
        x, y, w, h = cv2.boundingRect(cnt)
        
        # Draw bounding box
        cv2.rectangle(vis_img, (x-2, y-2), (x+w+2, y+h+2), color, 2)
        
        # Add label
        label_text = f"Q{i+1}: {label} ({mark}pt)"
        cv2.putText(vis_img, label_text, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        
        # Count classifications
        if label == "Tick":
            tick_count += 1
        else:
            cross_count += 1
        
        print(f"   Q{i+1:2d}: {label:5s} -> {mark} point(s)")
    
    # Add summary text
    total_score = tick_count
    summary_text = f"Score: {total_score}/{len(contours)} | Ticks: {tick_count} | Crosses: {cross_count}"
    cv2.putText(vis_img, summary_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 3)
    cv2.putText(vis_img, summary_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
    
    # Add legend
    legend_y = 70
    cv2.putText(vis_img, "Legend:", (10, legend_y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.putText(vis_img, "Green = Tick (Correct, 1 point)", (10, legend_y + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, tick_color, 2)
    cv2.putText(vis_img, "Red = Cross (Wrong, 0 points)", (10, legend_y + 50), cv2.FONT_HERSHEY_SIMPLEX, 0.6, cross_color, 2)
    
    # Save visualization
    base_name = os.path.splitext(os.path.basename(image_path))[0]
    output_path = f"visual_verification_{base_name}.jpg"
    cv2.imwrite(output_path, vis_img)
    
    print(f"✅ Visual verification saved: {output_path}")
    print(f"📊 Final Score: {total_score}/{len(contours)} ({total_score/len(contours)*100:.1f}%)")
    
    return total_score, len(contours)

def test_all_images():
    """Create visual verification for all test images"""
    print("🎨 CREATING VISUAL VERIFICATION FOR ALL IMAGES")
    print("=" * 60)
    
    test_images = [
        "uploads/c-1.jpeg",
        "uploads/c-2.jpeg",
        "uploads/C-1-2.jpeg",
        "test_marks.jpg",
        "test_shapes.jpg"
    ]
    
    total_marks = 0
    total_score = 0
    
    for img_path in test_images:
        if os.path.exists(img_path):
            score, marks = create_visual_verification(img_path)
            total_score += score
            total_marks += marks
            print()
        else:
            print(f"⚠️  Image not found: {img_path}\n")
    
    print("=" * 60)
    print("📊 OVERALL STATISTICS:")
    print(f"Total marks processed: {total_marks}")
    print(f"Total score: {total_score}")
    print(f"Overall percentage: {total_score/total_marks*100:.1f}%")
    print()
    print("🎯 SCORING SYSTEM EXPLANATION:")
    print("• Tick (✓) = Correct answer = 1 point")
    print("• Cross (✗) = Wrong answer = 0 points")
    print("• The system detects red ink marks and classifies them")
    print("• Green boxes = Detected ticks (correct answers)")
    print("• Red boxes = Detected crosses (wrong answers)")
    print()
    print("📁 Check the visual_verification_*.jpg files to see the results!")

if __name__ == "__main__":
    test_all_images()