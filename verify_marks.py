import cv2
import numpy as np
from utils.image_processing import classify_mark

def create_test_image():
    # White background
    img = np.zeros((200, 600, 3), dtype=np.uint8)
    img[:] = 255
    
    # Red color
    red = (0, 0, 255)
    thickness = 3
    
    # 1. Standard Tick (V)
    # (50, 50) -> (70, 90) -> (110, 30)
    cv2.line(img, (50, 50), (70, 90), red, thickness)
    cv2.line(img, (70, 90), (110, 30), red, thickness)
    cv2.putText(img, "Tick", (50, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,0), 1)

    # 2. Standard Cross (X)
    # (150, 30) -> (190, 90)
    # (190, 30) -> (150, 90)
    cv2.line(img, (150, 30), (190, 90), red, thickness)
    cv2.line(img, (190, 30), (150, 90), red, thickness)
    cv2.putText(img, "Cross", (150, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,0), 1)

    # 3. Squashed Cross (Flat X)
    # (250, 40) -> (290, 80)
    # (290, 40) -> (250, 80)
    # Make it wider/flatter
    cv2.line(img, (250, 50), (290, 70), red, thickness)
    cv2.line(img, (290, 50), (250, 70), red, thickness)
    cv2.putText(img, "Flat X", (250, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,0), 1)

    # 4. T-Shape (T)
    # Vertical (350, 30) -> (350, 90)
    # Horizontal (320, 30) -> (380, 30)
    cv2.line(img, (350, 30), (350, 90), red, thickness)
    cv2.line(img, (320, 30), (380, 30), red, thickness)
    cv2.putText(img, "T-Cross", (350, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,0), 1)

    # 5. Plus (+)
    # (450, 30) -> (450, 90)
    # (420, 60) -> (480, 60)
    cv2.line(img, (450, 30), (450, 90), red, thickness)
    cv2.line(img, (420, 60), (480, 60), red, thickness)
    cv2.putText(img, "Plus", (450, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,0), 1)
    
    cv2.imwrite("test_shapes.jpg", img)
    return "test_shapes.jpg"

def verify():
    img_path = create_test_image()
    img = cv2.imread(img_path)
    
    # Pre-process like in get_contours (simplified)
    # We just need contours of the red shapes
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    lower_red = np.array([0, 50, 50])
    upper_red = np.array([10, 255, 255])
    mask = cv2.inRange(hsv, lower_red, upper_red)
    
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Sort left to right
    contours = sorted(contours, key=lambda c: cv2.boundingRect(c)[0])
    
    expected = ["Tick", "Cross", "Cross", "Cross", "Cross"] # Flat X, T, Plus should be Cross
    
    print(f"Found {len(contours)} contours")
    
    for i, cnt in enumerate(contours):
        mark, label = classify_mark(cnt, img)
        print(f"Shape {i+1}: Expected {expected[i] if i < len(expected) else 'Unknown'}, Got {label} (Mark {mark})")

if __name__ == "__main__":
    verify()
