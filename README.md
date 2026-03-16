# 📋 Roll Number Recognizer — Blue Ink, Top-Right Corner

Automatically reads handwritten **roll numbers** written in **blue ink** in the **top-right corner** of exam/question papers.

---

## 📂 Files

```
roll_number_recognizer/
├── train_model.py        ← Train the CNN on MNIST (run once)
├── recognize_roll.py     ← Recognize roll number from ONE paper
├── batch_process.py      ← Process a FOLDER of papers → CSV output
├── calibrate.py          ← Visual check before running (recommended!)
├── requirements.txt
└── README.md
```

> ⚠️ Copy `train_model.py` from the previous project — the CNN is the same.

---

## 🚀 Step-by-Step Usage

### 1. Install
```bash
pip install -r requirements.txt
```

### 2. Train the model (once)
```bash
python train_model.py
```

### 3. CALIBRATE first (strongly recommended)
```bash
python calibrate.py your_sample_paper.jpg
```
This saves 4 debug images showing exactly what the system sees:
- `calib_1_full_page_with_zone.jpg` — red box showing where it looks
- `calib_2_cropped_region.jpg` — the actual crop
- `calib_3_blue_ink_mask.jpg` — blue ink isolated
- `calib_4_detected_digits.jpg` — individual digits boxed in green

### 4. Recognize a single paper
```bash
python recognize_roll.py exam_paper.jpg
```
Output:
```
Detected 6 digit(s):
────────────────────────────────────────
  Digit 1: 2  (confidence: 98.1%)
  Digit 2: 3  (confidence: 97.4%)
  ...
────────────────────────────────────────
  ✅  Roll Number: 230045
```

### 5. Process a whole folder (batch mode)
```bash
python batch_process.py path/to/papers/
```
Saves results to `roll_numbers_TIMESTAMP.csv`

---

## ⚙️ Tuning (if results are wrong)

Open `recognize_roll.py` and adjust these at the top:

```python
# How much of the page to look at
TOP_CROP_FRACTION   = 0.18   # increase if roll no. is lower on the page
RIGHT_CROP_FRACTION = 0.40   # increase if roll no. is more centered

# Blue ink color range (HSV)
BLUE_HSV_LOWER = np.array([90,  50,  50])   # lower = detect more blue shades
BLUE_HSV_UPPER = np.array([135, 255, 255])  # adjust for different ink brands
```

Use `calibrate.py` after each change to verify.

---

## 📸 Photo Tips for Best Results

| ✅ Do | ❌ Avoid |
|---|---|
| Flat paper, no folds | Crumpled/bent paper |
| Even bright lighting | Shadows across the roll number |
| Camera directly above | Angled/tilted shots |
| Blue ballpoint pen | Pencil, black pen, gel pen |
| Neat, separated digits | Digits touching each other |

---

## 🔁 Full Pipeline

```
Full Page Image
      │
      ▼
 Crop Top-Right (18% height × 40% width)
      │
      ▼
 HSV Blue Ink Mask  (filters out printed black text)
      │
      ▼
 Contour Detection  (finds each digit as a bounding box)
      │
      ▼
 Preprocess → 28×28 grayscale (MNIST format)
      │
      ▼
 CNN Prediction (per digit)
      │
      ▼
 Assemble Roll Number string
```
