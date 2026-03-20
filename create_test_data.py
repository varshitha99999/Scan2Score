import pandas as pd
import cv2
import numpy as np
import os

def create_dummy_data():
    # 1. Create Dummy Excel
    columns = ["S.No.", "Roll No."] + [f"Q{i}" for i in range(1, 21)] + ["Objective Total"]
    df = pd.DataFrame(columns=columns)
    df.to_excel("test_template.xlsx", index=False)
    print("Created test_template.xlsx")

    # 2. Create Dummy Image with Red Marks
    # White background
    img = np.ones((1000, 800, 3), dtype=np.uint8) * 255
    
    # Draw some "Ticks" (Red V shape)
    # Red in BGR is (0, 0, 255)
    
    # Q1: Tick
    # Draw two lines
    cv2.line(img, (700, 100), (710, 120), (0, 0, 255), 5)
    cv2.line(img, (710, 120), (730, 90), (0, 0, 255), 5)
    
    # Q2: Cross (Red X shape)
    cv2.line(img, (700, 200), (730, 230), (0, 0, 255), 5)
    cv2.line(img, (730, 200), (700, 230), (0, 0, 255), 5)
    
    # Q3: Tick
    cv2.line(img, (700, 300), (710, 320), (0, 0, 255), 5)
    cv2.line(img, (710, 320), (730, 290), (0, 0, 255), 5)
    
    # Q4: Cross
    cv2.line(img, (700, 400), (730, 430), (0, 0, 255), 5)
    cv2.line(img, (730, 400), (700, 430), (0, 0, 255), 5)
    
    cv2.imwrite("test_marks.jpg", img)
    print("Created test_marks.jpg")

if __name__ == "__main__":
    create_dummy_data()
