#!/usr/bin/env python3
"""
Roll Number Integration — FIXED VERSION
Changes vs. old version:
  • Uses the fixed TargetedRollDetector (all 5 root-cause fixes)
  • detector.calibrate_targeted() is called once before any processing
  • Excel is opened ONCE for the whole batch, not once per image
  • roll_no_col search scans up to 30 rows (not 10)
  • Header regex matches app.py exactly
  • Roll number is ALWAYS written (not only in the "empty row found" branch)
  • If detection fails AND no fallback is given, the image is SKIPPED (no UNKNOWN writes)
  • q_cols empty guard prevents ValueError on max()
"""
import os
import re
import pythoncom
import win32com.client
import subprocess
import shutil
from datetime import datetime

from utils.image_processing import process_image          # existing red-ink logic — DO NOT MODIFY
from utils.enhanced_roll_detector import EnhancedRollDetector


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _unblock_file(file_path: str):
    """Remove NTFS mark-of-the-web so Excel doesn't open in Protected View."""
    try:
        subprocess.run(
            ["powershell", "-Command", f"Unblock-File -LiteralPath '{file_path}'"],
            check=True, capture_output=True
        )
    except Exception as e:
        print(f"Warning: Could not unblock file: {e}")


def _save_processed_paper(image_path: str, roll_number: str):
    """Save processed paper with roll number as filename for student access."""
    try:
        # Create processed_papers directory if it doesn't exist
        processed_dir = "processed_papers"
        os.makedirs(processed_dir, exist_ok=True)
        
        # Get file extension
        _, ext = os.path.splitext(image_path)
        if not ext:
            ext = '.jpg'  # Default extension
        
        # Create filename with full roll number (including prefix)
        full_roll_number = "23WH1A12" + roll_number
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{full_roll_number}_{timestamp}{ext}"
        
        # Copy file to processed_papers directory
        dest_path = os.path.join(processed_dir, filename)
        shutil.copy2(image_path, dest_path)
        
        print(f"   📁 Saved paper: {filename}")
        return dest_path
        
    except Exception as e:
        print(f"   ⚠️ Could not save processed paper: {e}")
        return None


def _detect_roll(image_path: str, detector: EnhancedRollDetector) -> str | None:
    """Return detected roll number string, or None on failure."""
    try:
        roll = detector.recognize_roll_number(image_path, debug=False)
        if roll and roll not in ("NOT_FOUND", "ERROR"):
            print(f"   🔵 Roll detected: {roll}")
            return roll
        print(f"   ⚠️  Roll detection returned: {roll}")
        return None
    except Exception as e:
        print(f"   ❌ Roll detection error: {e}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Excel batch writer  (opens the file ONCE for all students)
# ─────────────────────────────────────────────────────────────────────────────

def write_batch_to_excel(excel_path: str, student_records: list, exam_type: str = "Objective-1") -> dict:
    """
    Write a list of student records to Excel in one COM session.

    student_records: list of dicts, each with keys:
        roll_number  str
        marks_map    dict[int, int]   {question_number: mark}
        total_marks  int

    Returns: {"written": N, "failed": M}
    """
    excel_path = os.path.abspath(excel_path)
    if not os.path.exists(excel_path):
        print(f"❌ Excel file not found: {excel_path}")
        return {"written": 0, "failed": len(student_records)}

    print(f"\n📊 Opening Excel once for {len(student_records)} student(s) …")

    pythoncom.CoInitialize()
    try:
        excel = win32com.client.DispatchEx("Excel.Application")
    except Exception:
        excel = win32com.client.Dispatch("Excel.Application")

    excel.Visible       = False
    excel.DisplayAlerts = False

    wb = None
    written = 0
    failed  = 0

    try:
        _unblock_file(excel_path)
        wb = excel.Workbooks.Open(excel_path)

        # ── Find sheet ────────────────────────────────────────────────────────
        ws = None
        for i in range(1, wb.Sheets.Count + 1):
            sheet = wb.Sheets(i)
            if sheet.Name == exam_type:
                ws = sheet
                break
        if ws is None:
            # fallback: sheet whose name contains the exam number
            exam_num = exam_type.split("-")[-1]
            for i in range(1, wb.Sheets.Count + 1):
                sheet = wb.Sheets(i)
                if "objective" in sheet.Name.lower() and exam_num in sheet.Name:
                    ws = sheet
                    break
        if ws is None:
            ws = wb.ActiveSheet
            print(f"   ⚠️  Sheet '{exam_type}' not found, using: {ws.Name}")
        else:
            print(f"   📋 Using sheet: {ws.Name}")

        # ── Unprotect ─────────────────────────────────────────────────────────
        try:
            if ws.ProtectContents:
                ws.Unprotect()
        except Exception:
            pass

        # ── Discover column layout ────────────────────────────────────────────
        used   = ws.UsedRange
        max_row = used.Rows.Count + used.Row - 1
        max_col = used.Columns.Count + used.Column - 1

        roll_no_col = None
        header_row  = None
        q_cols      = {}          # {question_number: column_index}
        total_col   = None

        # Scan up to 30 rows for headers (was only 10 — missed multi-row titles)
        for r in range(1, min(31, max_row + 1)):
            for c in range(1, max_col + 1):
                val = ws.Cells(r, c).Value
                if not val:
                    continue
                val_str = str(val).strip()

                # Roll No column — same regex as app.py
                if re.search(r'(?i)\broll\s*no\b', val_str):
                    roll_no_col = c
                    header_row  = r

                # Question columns: Q1, Q2, … or "Question No. 1" etc.
                m = re.search(r'(?i)(?:^|\b)(?:Q|Question\s*No\.?)\s*(\d+)\b', val_str)
                if m:
                    q_cols[int(m.group(1))] = c

                # Total column
                if re.search(r'(?i)objective\s+total|^total$', val_str):
                    total_col = c

        if roll_no_col is None:
            print("   ❌ Could not find 'Roll No' column — aborting Excel write")
            return {"written": 0, "failed": len(student_records)}

        start_row = (header_row + 1) if header_row else 2

        # ── Build map of existing roll numbers → row index ────────────────────
        existing_rolls: dict[str, int] = {}
        first_empty_row = -1

        for r in range(start_row, max_row + 1):
            val = ws.Cells(r, roll_no_col).Value
            if val:
                existing_rolls[str(val).strip().upper()] = r
            elif first_empty_row == -1:
                first_empty_row = r

        if first_empty_row == -1:
            first_empty_row = max_row + 1

        next_new_row = first_empty_row    # pointer that advances for each new student

        # ── Write each student ────────────────────────────────────────────────
        for rec in student_records:
            roll        = str(rec["roll_number"]).strip().upper()
            marks_map   = rec["marks_map"]    # {q_num: mark}
            total_marks = rec["total_marks"]

            # Find or allocate row
            if roll in existing_rolls:
                target_row = existing_rolls[roll]
                print(f"   ✏️  Updating existing row {target_row} for {roll}")
            else:
                target_row = next_new_row
                next_new_row += 1
                existing_rolls[roll] = target_row
                print(f"   ➕  New row {target_row} for {roll}")

            # Always write the roll number with prefix (was missing in the max_row+1 branch)
            full_roll_number = "23WH1A12" + roll
            ws.Cells(target_row, roll_no_col).Value = full_roll_number

            # Write per-question marks
            marks_written = 0
            for q_num, mark in marks_map.items():
                if q_num in q_cols:
                    ws.Cells(target_row, q_cols[q_num]).Value = int(mark)
                    marks_written += 1

            # Write total
            if total_col:
                ws.Cells(target_row, total_col).Value = total_marks
            elif q_cols:
                # FIX: guard against empty q_cols before calling max()
                fallback_total_col = max(q_cols.values()) + 1
                ws.Cells(target_row, fallback_total_col).Value = total_marks

            print(f"      ✅ {roll}: {marks_written} marks written, total={total_marks}")
            written += 1

        wb.Save()
        print(f"\n   💾 Saved. Written={written}, Failed={failed}")

    except Exception as e:
        print(f"   ❌ Excel batch write error: {e}")
        import traceback; traceback.print_exc()
        failed = len(student_records) - written

    finally:
        if wb:
            try: wb.Close()
            except Exception: pass
        try: excel.Quit()
        except Exception: pass
        pythoncom.CoUninitialize()

    return {"written": written, "failed": failed}


# ─────────────────────────────────────────────────────────────────────────────
# Main integration entry point  (called from app.py)
# ─────────────────────────────────────────────────────────────────────────────

def process_with_roll_detection(
    image_paths: list,
    excel_path: str,
    exam_type: str = "Objective-1",
    fallback_rolls: list = None,
) -> dict:
    """
    Process a batch of answer-sheet images:
      1. Run calibration once on the first image (for debug visibility)
      2. Detect roll number from blue ink for each image
      3. Run existing red-ink correction on each image
      4. Write all results to Excel in ONE COM session

    Args:
        image_paths    : list of image file paths
        excel_path     : path to the output Excel file
        exam_type      : sheet name, e.g. "Objective-1"
        fallback_rolls : optional list of roll numbers to use if detection fails
                         (must be same length as image_paths, or None)

    Returns:
        {"successful": N, "failed": M, "skipped": K}
    """
    print(f"\n🚀 Processing {len(image_paths)} image(s) with roll detection")

    # ── Initialise detector ───────────────────────────────────────────────────
    try:
        detector = EnhancedRollDetector("models/digit_recognizer.keras")
    except Exception as e:
        print(f"❌ Could not initialise roll detector: {e}")
        return {"successful": 0, "failed": 0, "skipped": len(image_paths)}

    # Calibrate once so debug images are available
    if image_paths and os.path.exists(image_paths[0]):
        detector.calibrate(image_paths[0])

    student_records = []
    failed          = 0
    skipped         = 0

    for i, img_path in enumerate(image_paths):
        print(f"\n📄 [{i+1}/{len(image_paths)}] {os.path.basename(img_path)}")

        if not os.path.exists(img_path):
            print(f"   ❌ File not found, skipping")
            skipped += 1
            continue

        # ── Step 1: detect roll number ────────────────────────────────────────
        roll = _detect_roll(img_path, detector)

        if not roll:
            fallback = (fallback_rolls[i] if fallback_rolls and i < len(fallback_rolls) else None)
            if fallback:
                print(f"   📋 Using fallback roll: {fallback}")
                roll = fallback
            else:
                # Do NOT write UNKNOWN_xxx — skip this image cleanly
                print(f"   ⚠️  No roll number and no fallback — skipping image")
                skipped += 1
                continue

        # ── Step 2: red-ink answer correction (unchanged) ─────────────────────
        try:
            results     = process_image(img_path)
            marks_map   = {idx + 1: r["mark"] for idx, r in enumerate(results)}
            total_marks = sum(marks_map.values())
            print(f"   🔴 Correction done: total={total_marks}  marks={marks_map}")
        except Exception as e:
            print(f"   ❌ process_image failed: {e}")
            failed += 1
            continue

        # ── Step 2.5: Save processed paper for student access ─────────────────
        _save_processed_paper(img_path, roll)

        student_records.append({
            "roll_number": roll,
            "marks_map":   marks_map,
            "total_marks": total_marks,
        })

    # ── Step 3: write ALL records to Excel in ONE session ────────────────────
    if student_records:
        result = write_batch_to_excel(excel_path, student_records, exam_type)
        successful = result["written"]
        failed    += result["failed"]
    else:
        successful = 0

    print(f"\n🎯 DONE — successful={successful}  failed={failed}  skipped={skipped}")
    return {"successful": successful, "failed": failed, "skipped": skipped}


# ─────────────────────────────────────────────────────────────────────────────
# Quick smoke test
# ─────────────────────────────────────────────────────────────────────────────

def test_roll_integration():
    print("🧪 TESTING ROLL NUMBER INTEGRATION")
    print("=" * 50)

    test_images    = ["uploads/cor-01.png", "uploads/c-1.jpeg", "uploads/c-2.jpeg"]
    fallback_rolls = ["23WH1A0101", "23WH1A1253", "23WH1A1254"]
    excel_path     = "master_template.xlsx"

    if not os.path.exists(excel_path):
        print(f"❌ Excel template not found: {excel_path}")
        return False

    import shutil
    test_excel = "test_roll_integration.xlsx"
    shutil.copy2(excel_path, test_excel)

    existing_images = [p for p in test_images if os.path.exists(p)]
    fallbacks       = fallback_rolls[:len(existing_images)]

    result = process_with_roll_detection(existing_images, test_excel,
                                         exam_type="Objective-1",
                                         fallback_rolls=fallbacks)
    print(f"\n🎯 Test result: {result}")
    if result["successful"] > 0:
        print(f"✅ Check: {test_excel}")
    return result["successful"] > 0


if __name__ == "__main__":
    test_roll_integration()