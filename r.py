import cv2
import numpy as np

img = cv2.imread("input/RedInkDetection.jpg")

# -------- LAB SPACE --------
lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
L, A, B = cv2.split(lab)

# Detect red using A channel (LOW threshold to catch faint ink)
lab_red = cv2.inRange(A, 135, 255)

# -------- HSV SPACE --------
hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
H, S, V = cv2.split(hsv)

# Red hue ranges-
hsv_red1 = cv2.inRange(hsv, (0, 40, 40), (10, 255, 255))
hsv_red2 = cv2.inRange(hsv, (160, 40, 40), (180, 255, 255))
hsv_red = cv2.bitwise_or(hsv_red1, hsv_red2)

# -------- RGB DOMINANCE --------
Bgr, Ggr, Rgr = cv2.split(img)
rgb_red = cv2.inRange(Rgr - Ggr, 20, 255)

# -------- FUSION --------
red_mask = cv2.bitwise_or(lab_red, hsv_red)
red_mask = cv2.bitwise_or(red_mask, rgb_red)

# -------- SAFE CLEANUP (DO NOT KILL STROKES) --------
kernel = np.ones((2,2), np.uint8)
red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_CLOSE, kernel, 1)

# -------- EXTRACT RED INK --------
red_only = cv2.bitwise_and(img, img, mask=red_mask)

cv2.imshow("Original", img)
cv2.imshow("Red Mask", red_mask)
cv2.imshow("All Red Ink Detected", red_only)
cv2.waitKey(0)
cv2.destroyAllWindows()
