"""
app.py — Interactive Multi-Digit Recognizer
Draw as many digits as you want on the canvas.
Hit "Predict All" (or lift the pen) to recognise every digit at once.
"""

import os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"
import tensorflow as tf
import cv2

import tkinter as tk
from tkinter import ttk, messagebox, font as tkfont

# ── Config ───────────────────────────────────────────────────────────────────
CANVAS_W    = 700
CANVAS_H    = 300
BRUSH_SIZE  = 20
MODEL_PATH  = "digit_recognizer.keras"

BG          = "#0f0f1a"
CARD        = "#1a1a2e"
ACCENT      = "#6c63ff"
GREEN       = "#4ecca3"
WHITE       = "#ffffff"
MUTED       = "#a0a0c0"


# ═══════════════════════════════════════════════════════════════════════════
def segment_and_predict(pil_gray: Image.Image, model):
    """
    Given a grayscale PIL image (white digits on black bg),
    return list of (x, y, w, h, digit, conf) sorted left→right.
    """
    gray = np.array(pil_gray, dtype=np.uint8)

    _, binary = cv2.threshold(gray, 30, 255, cv2.THRESH_BINARY)
    kernel    = cv2.getStructuringElement(cv2.MORPH_RECT, (4, 4))
    dilated   = cv2.dilate(binary, kernel, iterations=2)

    num_labels, _, stats, _ = cv2.connectedComponentsWithStats(dilated, 8)

    img_area = CANVAS_W * CANVAS_H
    min_area = img_area * 0.001

    boxes = []
    for i in range(1, num_labels):
        x    = stats[i, cv2.CC_STAT_LEFT]
        y    = stats[i, cv2.CC_STAT_TOP]
        w    = stats[i, cv2.CC_STAT_WIDTH]
        h    = stats[i, cv2.CC_STAT_HEIGHT]
        area = stats[i, cv2.CC_STAT_AREA]
        if area >= min_area:
            boxes.append([x, y, w, h])

    # Merge nearby boxes (broken strokes of same digit)
    boxes = _merge_boxes(sorted(boxes, key=lambda b: b[0]), gap=18)
    boxes.sort(key=lambda b: (b[1] // 80, b[0]))   # row-then-column order

    results = []
    for x, y, w, h in boxes:
        margin = max(4, int(min(w, h) * 0.12))
        x1 = max(0, x - margin);  y1 = max(0, y - margin)
        x2 = min(CANVAS_W, x + w + margin)
        y2 = min(CANVAS_H, y + h + margin)

        crop = pil_gray.crop((x1, y1, x2, y2))
        crop.thumbnail((20, 20), Image.LANCZOS)
        tile = Image.new("L", (28, 28), 0)
        tile.paste(crop, ((28 - crop.width) // 2, (28 - crop.height) // 2))
        tile = tile.filter(ImageFilter.GaussianBlur(0.5))

        arr   = np.array(tile, dtype="float32") / 255.0
        probs = model.predict(arr.reshape(1, 28, 28, 1), verbose=0)[0]
        digit = int(np.argmax(probs))
        conf  = float(probs[digit]) * 100
        results.append((x, y, w, h, digit, conf))

    return results


def _merge_boxes(boxes, gap=18):
    if not boxes:
        return boxes
    merged = [list(boxes[0])]
    for x, y, w, h in boxes[1:]:
        px, py, pw, ph = merged[-1]
        if x <= px + pw + gap and not (y > py + ph or y + h < py):
            nx = min(px, x);  ny = min(py, y)
            merged[-1] = [nx, ny, max(px+pw, x+w)-nx, max(py+ph, y+h)-ny]
        else:
            merged.append([x, y, w, h])
    return [tuple(b) for b in merged]


# ═══════════════════════════════════════════════════════════════════════════
class MultiDigitApp:

    def __init__(self, root):
        self.root   = root
        self.model  = self._load_model()
        self._build_ui()
        self.drawing   = False
        self.last_x = self.last_y = None
        self.pil_img   = Image.new("L", (CANVAS_W, CANVAS_H), 0)
        self.pil_draw  = ImageDraw.Draw(self.pil_img)
        self.results   = []

    # ── Load ─────────────────────────────────────────────────────────────────
    def _load_model(self):
        if not os.path.exists(MODEL_PATH):
            messagebox.showerror("Model not found",
                f"'{MODEL_PATH}' not found.\nRun train_model.py first.")
            sys.exit(1)
        m = tf.keras.models.load_model(MODEL_PATH)
        return m

    # ── UI ───────────────────────────────────────────────────────────────────
    def _build_ui(self):
        self.root.title("Multi-Digit Handwriting Recognizer")
        self.root.configure(bg=BG)
        self.root.resizable(False, False)

        # Header
        tk.Label(self.root, text="✍  Multi-Digit Recognizer",
                 font=("Segoe UI", 18, "bold"), bg=BG, fg=ACCENT
                 ).pack(pady=(14, 2))
        tk.Label(self.root,
                 text="Write as many digits as you like — spaces between them",
                 font=("Segoe UI", 10), bg=BG, fg=MUTED
                 ).pack(pady=(0, 10))

        # Drawing canvas
        self.canvas = tk.Canvas(self.root, width=CANVAS_W, height=CANVAS_H,
                                bg="black", cursor="crosshair",
                                highlightthickness=2,
                                highlightbackground=ACCENT)
        self.canvas.pack(padx=20)
        self.canvas.bind("<ButtonPress-1>",   self._start)
        self.canvas.bind("<B1-Motion>",       self._draw)
        self.canvas.bind("<ButtonRelease-1>", self._stop)

        # Result strip (coloured boxes showing each detected digit)
        self.result_frame = tk.Frame(self.root, bg=CARD, height=70)
        self.result_frame.pack(fill="x", padx=20, pady=(8, 0))
        self.result_frame.pack_propagate(False)

        self.result_label = tk.Label(self.result_frame,
                                     text="Draw digits above, then click Predict All",
                                     font=("Segoe UI", 13), bg=CARD, fg=MUTED)
        self.result_label.pack(expand=True)

        # Full number display
        self.number_var = tk.StringVar(value="")
        tk.Label(self.root, textvariable=self.number_var,
                 font=("Courier New", 42, "bold"), bg=BG, fg=GREEN
                 ).pack(pady=(4, 0))

        # Buttons
        btn_row = tk.Frame(self.root, bg=BG)
        btn_row.pack(pady=12)
        bkw = dict(font=("Segoe UI", 12, "bold"), relief="flat",
                   cursor="hand2", padx=18, pady=7)
        tk.Button(btn_row, text="Predict All", command=self._predict_all,
                  bg=ACCENT, fg=WHITE, **bkw).pack(side="left", padx=8)
        tk.Button(btn_row, text="Clear",       command=self._clear,
                  bg="#2a2a4a", fg=MUTED, **bkw).pack(side="left", padx=8)

    # ── Drawing ───────────────────────────────────────────────────────────────
    def _start(self, e):
        self.drawing = True
        self.last_x, self.last_y = e.x, e.y

    def _draw(self, e):
        if not self.drawing:
            return
        r = BRUSH_SIZE // 2
        x, y = e.x, e.y
        self.canvas.create_oval(x-r, y-r, x+r, y+r, fill=WHITE, outline=WHITE)
        if self.last_x is not None:
            self.canvas.create_line(self.last_x, self.last_y, x, y,
                                    width=BRUSH_SIZE, fill=WHITE,
                                    capstyle=tk.ROUND, smooth=True)
        self.pil_draw.ellipse([x-r, y-r, x+r, y+r], fill=255)
        if self.last_x is not None:
            self.pil_draw.line([self.last_x, self.last_y, x, y],
                               fill=255, width=BRUSH_SIZE)
        self.last_x, self.last_y = x, y

    def _stop(self, e):
        self.drawing = False
        self.last_x = self.last_y = None
        self._predict_all()   # auto-predict on pen-up

    # ── Predict ───────────────────────────────────────────────────────────────
    def _predict_all(self):
        if self.pil_img.getbbox() is None:
            return

        self.results = segment_and_predict(self.pil_img, self.model)

        if not self.results:
            self.result_label.config(text="Nothing detected — try drawing larger digits")
            self.number_var.set("")
            return

        # Redraw canvas with coloured bounding boxes
        self._draw_boxes()

        # Build number string
        number_str = "".join(str(d) for *_, d, c in self.results)
        self.number_var.set(number_str)

        # Show confidence strip
        self._update_result_strip()

    def _draw_boxes(self):
        """Overlay coloured bounding boxes on the Tkinter canvas."""
        # Remove old box tags
        self.canvas.delete("bbox")
        colors = ["#6c63ff", "#4ecca3", "#ff6b6b", "#ffd93d",
                  "#a8edea", "#f7971e", "#ee0979", "#4facfe"]
        for i, (x, y, w, h, digit, conf) in enumerate(self.results):
            col = colors[i % len(colors)]
            self.canvas.create_rectangle(x, y, x+w, y+h,
                                         outline=col, width=2, tags="bbox")
            self.canvas.create_text(x + w//2, max(y - 12, 10),
                                    text=f"{digit}",
                                    font=("Segoe UI", 14, "bold"),
                                    fill=col, tags="bbox")

    def _update_result_strip(self):
        # Clear result frame
        for w in self.result_frame.winfo_children():
            w.destroy()

        inner = tk.Frame(self.result_frame, bg=CARD)
        inner.pack(expand=True)

        colors = ["#6c63ff", "#4ecca3", "#ff6b6b", "#ffd93d",
                  "#a8edea", "#f7971e", "#ee0979", "#4facfe"]

        for i, (*_, digit, conf) in enumerate(self.results):
            col = colors[i % len(colors)]
            cell = tk.Frame(inner, bg=col, padx=8, pady=4)
            cell.pack(side="left", padx=4, pady=8)
            tk.Label(cell, text=str(digit),
                     font=("Segoe UI", 22, "bold"),
                     bg=col, fg="black").pack()
            tk.Label(cell, text=f"{conf:.0f}%",
                     font=("Segoe UI", 8),
                     bg=col, fg="#333").pack()

    # ── Clear ─────────────────────────────────────────────────────────────────
    def _clear(self):
        self.canvas.delete("all")
        self.pil_img  = Image.new("L", (CANVAS_W, CANVAS_H), 0)
        self.pil_draw = ImageDraw.Draw(self.pil_img)
        self.results  = []
        self.number_var.set("")
        for w in self.result_frame.winfo_children():
            w.destroy()
        self.result_label = tk.Label(self.result_frame,
                                     text="Draw digits above, then click Predict All",
                                     font=("Segoe UI", 13), bg=CARD, fg=MUTED)
        self.result_label.pack(expand=True)


# ═══════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    root = tk.Tk()
    MultiDigitApp(root)
    root.mainloop()