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

# CRITICAL: Import protobuf fix FIRST
import fix_protobuf

# CRITICAL: Set environment variables BEFORE any imports
import os
os.environ['PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION'] = 'python'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'

# Suppress protobuf warnings
import warnings
warnings.filterwarnings('ignore', category=UserWarning, module='google.protobuf')

import re
import pythoncom
import win32com.client
import subprocess
import shutil
from datetime import datetime

from utils.image_processing import process_image          # existing red-ink logic — DO NOT MODIFY

# Safe import of roll detector with error handling
try:
    from utils.enhanced_roll_detector import EnhancedRollDetector
    ROLL_DETECTOR_AVAILABLE = True
    print("✅ Roll detector loaded successfully")
except ImportError as e:
    EnhancedRollDetector = None
    ROLL_DETECTOR_AVAILABLE = False
    print(f"Warning: Roll detector not available: {e}")


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


def _detect_roll(image_path: str, detector) -> str | None:
    """Return detected roll number string, or None on failure."""
    if detector is None:
        print("   ⚠️ Roll detector not available")
        return None
        
    try:
        roll = detector.recognize_roll_number(image_path, debug=False)
        if roll and roll not in ("NOT_FOUND", "ERROR", "UNKNOWN"):
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

        # ── Sort student records by roll number for ordered writing ───────────
        def extract_roll_number(record):
            """Extract numeric part from roll number for sorting"""
            roll = str(record["roll_number"]).strip().upper()
            # Handle different roll number formats
            if roll.startswith("23WH1A12"):
                # Extract the last 2 digits for sorting (e.g., "23WH1A1201" -> 1, "23WH1A1203" -> 3)
                suffix = roll.replace("23WH1A12", "")
                try:
                    return int(suffix)
                except:
                    return 0
            else:
                # For other formats, extract all numbers and use the last one
                import re
                numbers = re.findall(r'\d+', roll)
                if numbers:
                    return int(numbers[-1])
                return 0
        
        # Sort records by roll number
        sorted_records = sorted(student_records, key=extract_roll_number)
        print(f"   📋 Writing {len(sorted_records)} records in roll number order")
        
        # Debug: show the sorting order
        for rec in sorted_records:
            roll = str(rec["roll_number"]).strip().upper()
            sort_key = extract_roll_number(rec)
            print(f"      📝 Roll: {roll} -> Sort key: {sort_key}")

        # ── Write each student ────────────────────────────────────────────────
        for rec in sorted_records:
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

            # Check if this is an absentee (empty marks_map)
            is_absentee = not marks_map or all(mark == 0 for mark in marks_map.values())

            if is_absentee:
                # For absentees: write roll number exactly as entered (no prefix)
                ws.Cells(target_row, roll_no_col).Value = roll
                
                # Clear all question marks and total
                for q_num in range(1, 21):
                    if q_num in q_cols:
                        ws.Cells(target_row, q_cols[q_num]).Value = ""
                
                # Clear total
                if total_col:
                    ws.Cells(target_row, total_col).Value = ""
                elif q_cols:
                    fallback_total_col = max(q_cols.values()) + 1
                    ws.Cells(target_row, fallback_total_col).Value = ""
                
                print(f"      ✅ {roll}: ABSENTEE - roll number entered, all marks cleared")
            else:
                # For present students: write roll number with prefix
                full_roll_number = "23WH1A12" + roll
                ws.Cells(target_row, roll_no_col).Value = full_roll_number

                # Write per-question marks for present students
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
    pages_per_student: int = 1,
    absentees: list = None,
) -> dict:
    """
    Process a batch of answer-sheet images:
      1. Run calibration once on the first image (for debug visibility)
      2. Group images by student based on pages_per_student
      3. Detect roll number from blue ink for each student (from first page)
      4. Run existing red-ink correction on all pages for each student
      5. Add absentees with empty marks
      6. Write all results to Excel in ONE COM session

    Args:
        image_paths       : list of image file paths
        excel_path        : path to the output Excel file
        exam_type         : sheet name, e.g. "Objective-1"
        fallback_rolls    : optional list of roll numbers to use if detection fails
                           (must be same length as number of students, or None)
        pages_per_student : number of pages per student (1 for single side, 2 for front & back)
        absentees         : list of roll numbers for absentee students (will have empty marks)

    Returns:
        {"successful": N, "failed": M, "skipped": K}
    """
    print(f"\n🚀 Processing {len(image_paths)} image(s) with roll detection")
    print(f"📄 Pages per student: {pages_per_student}")
    
    if absentees:
        print(f"👥 Absentees: {absentees}")

    # ── Initialise detector ───────────────────────────────────────────────────
    detector = None
    if ROLL_DETECTOR_AVAILABLE:
        try:
            detector = EnhancedRollDetector("models/digit_recognizer.keras")
            print("✅ Roll detector initialized successfully")
        except Exception as e:
            print(f"❌ Could not initialise roll detector: {e}")
            detector = None
    else:
        print("⚠️ Roll detector not available - TensorFlow/protobuf compatibility issue")
    
    if detector is None:
        print("⚠️ Proceeding without roll number detection - using sequential assignment")

    # Calibrate once so debug images are available
    if detector and image_paths and os.path.exists(image_paths[0]):
        try:
            detector.calibrate(image_paths[0])
        except Exception as e:
            print(f"⚠️ Calibration failed: {e}")

    # ── Group images by student ───────────────────────────────────────────────
    student_image_groups = []
    for i in range(0, len(image_paths), pages_per_student):
        group = image_paths[i:i + pages_per_student]
        if len(group) == pages_per_student:  # Only process complete groups
            student_image_groups.append(group)
        else:
            print(f"⚠️  Incomplete group with {len(group)} images (expected {pages_per_student}), skipping")

    print(f"👥 Grouped into {len(student_image_groups)} student(s)")

    student_records = []
    failed          = 0
    skipped         = 0

    # ── Process uploaded images (present students) ────────────────────────────
    for student_idx, student_images in enumerate(student_image_groups):
        print(f"\n👤 Student {student_idx + 1}/{len(student_image_groups)}")
        print(f"   📄 Processing {len(student_images)} page(s): {[os.path.basename(p) for p in student_images]}")

        # Check if all files exist
        missing_files = [img for img in student_images if not os.path.exists(img)]
        if missing_files:
            print(f"   ❌ Missing files: {missing_files}, skipping student")
            skipped += 1
            continue

        # ── Step 1: detect roll number from first page (front page) ───────────
        front_page = student_images[0]
        roll = None
        
        # Try roll detection if available
        if detector:
            roll = _detect_roll(front_page, detector)
        
        # Fallback logic
        if not roll:
            fallback = (fallback_rolls[student_idx] if fallback_rolls and student_idx < len(fallback_rolls) else None)
            if fallback:
                print(f"   📋 Using fallback roll: {fallback}")
                roll = fallback
            elif not detector:
                # If no detector available, use sequential assignment
                sequential_roll = f"{student_idx + 1:02d}"  # 01, 02, 03, etc.
                print(f"   📋 Using sequential assignment: {sequential_roll}")
                roll = sequential_roll
            else:
                # Do NOT write UNKNOWN_xxx — skip this student cleanly
                print(f"   ⚠️  No roll number detected and no fallback — skipping student")
                skipped += 1
                continue

        # ── Step 2: red-ink answer correction for all pages ───────────────────
        try:
            all_marks = {}
            question_counter = 1
            
            for page_idx, img_path in enumerate(student_images):
                print(f"   📄 Processing page {page_idx + 1}: {os.path.basename(img_path)}")
                
                results = process_image(img_path)
                page_marks = {question_counter + idx: r["mark"] for idx, r in enumerate(results)}
                all_marks.update(page_marks)
                question_counter += len(results)
                
                print(f"      🔴 Page {page_idx + 1} marks: {list(page_marks.values())} (questions {min(page_marks.keys())}-{max(page_marks.keys())})")
            
            total_marks = sum(all_marks.values()) * 0.5  # Multiply total by 0.5
            print(f"   ✅ Student {roll}: total={total_marks} from {len(all_marks)} questions (multiplied by 0.5)")
            print(f"      📊 All marks: {all_marks}")
            
        except Exception as e:
            print(f"   ❌ process_image failed for student {roll}: {e}")
            failed += 1
            continue

        # ── Step 2.5: Save processed paper for student access (use first page) ─
        _save_processed_paper(front_page, roll)

        student_records.append({
            "roll_number": roll,
            "marks_map":   all_marks,
            "total_marks": total_marks,
        })

    # ── Process absentees (empty marks) ───────────────────────────────────────
    if absentees:
        print(f"\n👥 Processing {len(absentees)} absentee(s)")
        for absentee_roll in absentees:
            print(f"   📝 Adding absentee: {absentee_roll} (empty marks)")
            student_records.append({
                "roll_number": absentee_roll,
                "marks_map":   {},  # Empty marks for absentees
                "total_marks": 0,   # Zero total for absentees
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