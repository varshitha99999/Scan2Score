#!/usr/bin/env python3
"""
Test script to verify red ink marks processing
"""
from utils.image_processing import process_image
import os

def test_marks_processing():
    print("🔍 Testing Red Ink Marks Processing")
    print("=" * 40)
    
    # Test with available images
    test_images = [
        "test_marks.jpg",
        "test_shapes.jpg",
        "uploads/c-1.jpeg",
        "uploads/c-2.jpeg"
    ]
    
    for img_path in test_images:
        if os.path.exists(img_path):
            print(f"\n📸 Processing: {img_path}")
            try:
                results = process_image(img_path)
                print(f"✅ Found {len(results)} marks")
                
                # Show first 10 results
                for i, r in enumerate(results[:10]):
                    print(f"  Q{r['question_index']:2d}: {r['label']:5s} -> {r['mark']}")
                
                if len(results) > 10:
                    print(f"  ... and {len(results) - 10} more marks")
                    
                # Show marks mapping (how it's used in AI detection)
                marks_map = {i+1: r['mark'] for i, r in enumerate(results)}
                print(f"📊 Marks map sample: {dict(list(marks_map.items())[:5])}")
                
            except Exception as e:
                print(f"❌ Error processing {img_path}: {e}")
        else:
            print(f"⚠️  Image not found: {img_path}")
    
    print("\n" + "=" * 40)
    print("✅ Marks processing test completed!")

if __name__ == "__main__":
    test_marks_processing()