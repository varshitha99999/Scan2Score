#!/usr/bin/env python3
"""
Targeted Roll Number Detector — v3 (handles "01", thin "1", large handwriting)

Root causes fixed in this version:
  1. RETR_CCOMP + hierarchy filter  → skip inner holes of "0" (was producing false "4")
  2. Aspect ratio filter was INVERTED — it was rejecting tall-thin digits like "1"
     Old:  aspect = h/w,  filter: aspect < 0.6  → rejected "1" (h/w ~ 5-8)  <- WRONG
     New:  filter: bw > bh * 3.5  → rejects only wide flat noise, keeps all digits
  3. Area minimum lowered to 8      → thin "1" strokes have very low fill area
  4. Dimension limits widened       → large exam handwriting (up to 300-350px)
  5. Crop always at top=0           → digits flush with page top not clipped
  6. MORPH_OPEN removed             → thin strokes no longer erased
  7. Box merging gap = 20px         → arc fragments of same digit joined
  8. Padding before resize          → thin "1" not distorted into unrecognisable shape
  9. HSV strictly blue only         → black printed text excluded (S < 40 = black)
"""

import cv2
import numpy as np
import tensorflow as tf
from typing import List, Tuple, Optional
import os


class TargetedRollDetector:
    """
    Detects handwritten roll numbers written in blue ink.
    Completely ignores black printed text (black ink has S < 40 in HSV).
    """

    # Blue ink HSV range (OpenCV 0-180 hue scale)
    # H=90-130 covers ballpoint/gel/fountain blue
    # S>=40 excludes black ink, gray, white paper
    BLUE_HSV_LOWER = np.array([90,  40,  40])
    BLUE_HSV_UPPER = np.array([130, 255, 255])

    def __init__(self, model_path: str = "models/digit_recognizer.keras"):
        self.model_path = model_path
        self.model      = None
        self._load_model()

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def recognize_roll_number(self, image_path: str, debug: bool = False) -> str:
        """
        Detect the blue-ink roll number from an exam sheet image.
        Returns detected string e.g. "01", "23WH1A1253".
        Returns "NOT_FOUND" or "ERROR" on failure.
        """
        if self.model is None:
            return "ERROR"

        try:
            image = cv2.imread(image_path)
            if image is None:
                print(f"Could not load image: {image_path}")
                return "ERROR"

            # All regions start at top=0.0 so digits at the very top edge are never clipped
            regions = [
                {"name": "top_right_primary",  "top": 0.00, "bottom": 0.18, "left": 0.72, "right": 1.00},
                {"name": "top_right_extended", "top": 0.00, "bottom": 0.22, "left": 0.65, "right": 1.00},
                {"name": "top_right_wide",     "top": 0.00, "bottom": 0.25, "left": 0.58, "right": 1.00},
            ]

            best_result = None
            best_score  = -9999.0

            for region in regions:
                if debug:
                    print(f"\n  Region: {region['name']}")

                result = self._detect_in_region(image, region, debug)
                if not result:
                    continue

                roll   = result["roll_number"]
                length = len(roll)
                avg_c  = float(np.mean(result["confidences"])) if result["confidences"] else 0.0

                if roll in ("NOT_FOUND", "ERROR", "") or length == 0:
                    continue

                if 1 <= length <= 12:
                    score = avg_c - (length * 1.5)
                    if debug:
                        print(f"    -> '{roll}'  conf={avg_c:.1f}%  score={score:.1f}")
                    if score > best_score:
                        best_result = result
                        best_score  = score

            if best_result:
                if debug:
                    print(f"\n  Final result: '{best_result['roll_number']}'")
                return best_result["roll_number"]

            if debug:
                print("\n  No roll number found in any region")
            return "NOT_FOUND"

        except Exception as e:
            print(f"recognize_roll_number error: {e}")
            return "ERROR"

    def calibrate_targeted(self, image_path: str) -> bool:
        """Save debug images for each pipeline step."""
        print(f"CALIBRATION: {image_path}")
        try:
            image = cv2.imread(image_path)
            if image is None:
                print(f"Cannot load: {image_path}")
                return False

            h, w = image.shape[:2]
            regions = [
                {"name": "top_right_primary",  "top": 0.00, "bottom": 0.18, "left": 0.72, "right": 1.00},
                {"name": "top_right_extended", "top": 0.00, "bottom": 0.22, "left": 0.65, "right": 1.00},
                {"name": "top_right_wide",     "top": 0.00, "bottom": 0.25, "left": 0.58, "right": 1.00},
            ]

            marked  = image.copy()
            colours = [(0, 0, 255), (0, 200, 0), (255, 128, 0)]
            for i, reg in enumerate(regions):
                t = int(h * reg["top"]);  b = int(h * reg["bottom"])
                l = int(w * reg["left"]); r = int(w * reg["right"])
                cv2.rectangle(marked, (l, t), (r, b), colours[i], 3)
                cv2.putText(marked, f"R{i+1}", (l + 4, t + 28),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.9, colours[i], 2)
            cv2.imwrite("calib_0_regions.jpg", marked)

            for reg in regions:
                result = self._detect_in_region(image, reg, debug=True)
                found  = f"'{result['roll_number']}'" if result else "not found"
                print(f"  {reg['name']:30s} -> {found}")

            print("Done - check calib_*.jpg and debug_*.jpg")
            return True

        except Exception as e:
            print(f"Calibration error: {e}")
            return False

    # -------------------------------------------------------------------------
    # Internal pipeline
    # -------------------------------------------------------------------------

    def _detect_in_region(self, image: np.ndarray, region: dict,
                          debug: bool = False) -> Optional[dict]:
        try:
            h, w = image.shape[:2]
            roi = image[
                int(h * region["top"])  : int(h * region["bottom"]),
                int(w * region["left"]) : int(w * region["right"])
            ]
            if roi.size == 0:
                return None

            if debug:
                cv2.imwrite(f"debug_1_roi_{region['name']}.jpg", roi)

            # Step 1: isolate blue pixels only
            mask = self._create_blue_mask(roi)
            if debug:
                cv2.imwrite(f"debug_2_mask_{region['name']}.jpg", mask)
                blue_px = int(np.count_nonzero(mask))
                print(f"    blue pixels in mask: {blue_px}")

            # Step 2: find digit bounding boxes
            boxes = self._find_digit_boxes(mask, debug)
            if not boxes:
                return None

            if debug:
                vis = roi.copy()
                for (x, y, bw, bh) in boxes:
                    cv2.rectangle(vis, (x, y), (x + bw, y + bh), (0, 255, 0), 2)
                cv2.imwrite(f"debug_3_boxes_{region['name']}.jpg", vis)

            # Step 3: run CNN on each box
            digits      = []
            confidences = []

            for bx, by, bw, bh in boxes:
                crop = mask[by: by + bh, bx: bx + bw]
                arr  = self._preprocess_digit(crop)
                pred = self.model.predict(arr.reshape(1, 28, 28, 1), verbose=0)[0]
                d    = int(np.argmax(pred))
                c    = float(np.max(pred)) * 100.0

                if debug:
                    print(f"    box({bx},{by},{bw},{bh}) area={bw*bh} -> digit={d} conf={c:.1f}%")

                if c >= 35.0:
                    digits.append(str(d))
                    confidences.append(c)

            if not digits:
                return None

            return {"roll_number": "".join(digits), "confidences": confidences}

        except Exception as e:
            if debug:
                print(f"    _detect_in_region error: {e}")
            return None

    def _create_blue_mask(self, roi: np.ndarray) -> np.ndarray:
        """
        Binary mask: white = blue ink pixels, black = everything else.

        Black printed text is excluded because:
          - Black ink in HSV has S (saturation) < 30 and V (brightness) < 80
          - Our lower bound requires S >= 40, so ALL near-black pixels are excluded
          - This means printed questions, options, labels are invisible here
        """
        hsv  = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, self.BLUE_HSV_LOWER, self.BLUE_HSV_UPPER)

        # CLOSE: fills small gaps within strokes (good for "0" ring)
        # NO OPEN: MORPH_OPEN removes small blobs — destroys thin "1" strokes
        kernel = np.ones((2, 2), np.uint8)
        mask   = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        return mask

    def _find_digit_boxes(self, mask: np.ndarray,
                          debug: bool = False) -> List[Tuple[int, int, int, int]]:
        """
        Return left-to-right sorted bounding boxes of digit contours.

        THE KEY FIX — aspect ratio was inverted in all previous versions:
          WRONG (old): aspect = h/w;  if aspect < 0.6: skip
                       This rejects digits where h > 0.6*w
                       The "1" has h/w ~ 5-8, so it was ALWAYS skipped
          CORRECT:     if bw > bh * 3.5: skip
                       Only rejects wide-flat shapes (underlines, noise bars)
                       Keeps "0" (bw ~ bh), "1" (bh >> bw), and all other digits
        """
        contours, hierarchy = cv2.findContours(
            mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE
        )

        if hierarchy is None or len(contours) == 0:
            return []

        boxes = []
        for i, cnt in enumerate(contours):
            # Skip inner holes (the white void inside "0")
            # hierarchy: [next, prev, first_child, parent]
            # parent != -1 means this contour is nested inside another
            if hierarchy[0][i][3] != -1:
                continue

            area             = cv2.contourArea(cnt)
            x, y, bw, bh    = cv2.boundingRect(cnt)

            # Area filter — low enough to catch thin "1" (area can be ~50-200px)
            if area < 8 or area > 150_000:
                continue

            # Dimension filter — large handwriting can be up to ~300px tall
            if bw < 3 or bw > 300:
                continue
            if bh < 10 or bh > 350:
                continue

            # Aspect ratio filter — FIXED
            # Only reject shapes much wider than tall (underlines, horizontal smudges)
            if bw > bh * 3.5:
                continue

            boxes.append((x, y, bw, bh))

        if debug:
            print(f"    raw boxes ({len(boxes)}): {boxes}")

        # Merge boxes that belong to the same digit (arc fragments of "0")
        boxes = self._merge_nearby_boxes(boxes, gap=20)

        boxes.sort(key=lambda b: b[0])

        if debug:
            print(f"    merged boxes ({len(boxes)}): {boxes}")

        return boxes

    @staticmethod
    def _merge_nearby_boxes(
        boxes: List[Tuple[int, int, int, int]], gap: int = 20
    ) -> List[Tuple[int, int, int, int]]:
        """
        Merge horizontally adjacent boxes within `gap` pixels.
        Joins arc-fragments of the same digit.
        The "0" and "1" in "01" are separated by more than 20px so they stay separate.
        """
        if not boxes:
            return []

        boxes  = sorted(boxes, key=lambda b: b[0])
        merged = [list(boxes[0])]

        for x, y, w, h in boxes[1:]:
            px, py, pw, ph = merged[-1]
            if x <= px + pw + gap:
                nx = min(px, x)
                ny = min(py, y)
                nw = max(px + pw, x + w) - nx
                nh = max(py + ph, y + h) - ny
                merged[-1] = [nx, ny, nw, nh]
            else:
                merged.append([x, y, w, h])

        return [tuple(b) for b in merged]

    @staticmethod
    def _preprocess_digit(crop: np.ndarray) -> np.ndarray:
        """
        Resize to 28x28 and normalise for MNIST-format CNN input.
        Adds padding first so thin digits like "1" are not squashed
        when resized to a square — without padding "1" becomes a thick
        blob that the model may not recognise correctly.
        """
        if crop.size == 0:
            return np.zeros((28, 28), dtype=np.float32)

        # Pad by 25% of the larger dimension on each side
        pad    = max(crop.shape[0], crop.shape[1]) // 4
        padded = cv2.copyMakeBorder(
            crop, pad, pad, pad, pad,
            cv2.BORDER_CONSTANT, value=0
        )
        resized = cv2.resize(padded, (28, 28))
        return resized.astype(np.float32) / 255.0

    def _load_model(self):
        try:
            if os.path.exists(self.model_path):
                self.model = tf.keras.models.load_model(self.model_path)
                print(f"Model loaded: {self.model_path}")
            else:
                print(f"Model not found: {self.model_path}")
        except Exception as e:
            print(f"Model load error: {e}")


# -------------------------------------------------------------------------
# Standalone test
# -------------------------------------------------------------------------
def test_targeted_detection():
    print("TESTING TARGETED ROLL NUMBER DETECTION")
    print("=" * 55)

    test_images = ["uploads/cor-01.png", "uploads/c-1.jpeg", "uploads/c-2.jpeg"]
    detector    = TargetedRollDetector()

    for path in test_images:
        if not os.path.exists(path):
            print(f"Not found: {path}")
            continue
        print(f"\nImage: {os.path.basename(path)}")
        detector.calibrate_targeted(path)
        result = detector.recognize_roll_number(path, debug=True)
        print(f"RESULT: {result}")
        print("-" * 55)


if __name__ == "__main__":
    test_targeted_detection()