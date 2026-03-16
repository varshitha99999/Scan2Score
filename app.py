import os
import time
import subprocess
import random
import zipfile
import io
from flask import Flask, render_template, request, send_file, session, redirect, url_for
from werkzeug.utils import secure_filename
from utils.image_processing import process_image
import re
import pythoncom
import win32com.client
import shutil
from fpdf import FPDF
import copy

app = Flask(__name__)
app.secret_key = 'scan2score_secret_key_2026'  # Change this to a random secret key in production
app.config['UPLOAD_FOLDER'] = os.path.abspath('uploads')
app.config['Result_FOLDER'] = os.path.abspath('results')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['Result_FOLDER'], exist_ok=True)

# User credentials database
USERS = {
    # Teachers
    'teacher@college.com': {'password': 'teacher123', 'type': 'teacher', 'name': 'Dr. Faculty'},
    'teacher': {'password': 'teacher123', 'type': 'teacher', 'name': 'Dr. Faculty'},
    'admin': {'password': 'admin123', 'type': 'teacher', 'name': 'Admin Teacher'},
    'faculty@scan2score.com': {'password': 'faculty123', 'type': 'teacher', 'name': 'Faculty Member'},
    
    # Students
    'student': {'password': 'student123', 'type': 'student', 'name': 'Student User'},
    'student@scan2score.com': {'password': 'student123', 'type': 'student', 'name': 'John Doe'},
    '24WH1A0501': {'password': 'student123', 'type': 'student', 'name': 'Student 501'},
}

def natural_sort_key(s):
    return [int(text) if text.isdigit() else text.lower() for text in re.split('([0-9]+)', s)]

def unblock_file(file_path):
    """Unblocks a file downloaded from the internet to prevent Protected View issues."""
    try:
        subprocess.run(["powershell", "-Command", f"Unblock-File -LiteralPath '{file_path}'"], check=True, capture_output=True)
    except Exception as e:
        print(f"Warning: Could not unblock file: {e}")

def generate_roll_numbers(start, end):
    if len(start) >= 2 and len(end) >= 2:
        prefix_start, suffix_start = start[:-2], start[-2:]
        prefix_end, suffix_end = end[:-2], end[-2:]

        if prefix_start == prefix_end:
            def is_valid_suffix(s):
                if s.isdigit():
                    v = int(s)
                    return 1 <= v <= 99
                if len(s) == 2 and s[0].isalpha() and s[1].isdigit():
                    d = int(s[1])
                    return 0 <= d <= 9
                return False

            def suffix_to_order(s):
                if s.isdigit():
                    return int(s)
                letter = s[0].upper()
                d = int(s[1])
                base = 99
                idx = ord(letter) - ord('A')
                return base + idx * 10 + (d + 1)

            def order_to_suffix(n):
                if n <= 99:
                    return str(n).zfill(2)
                base = n - 99
                idx = (base - 1) // 10
                d = (base - 1) % 10
                letter = chr(ord('A') + idx)
                return f"{letter}{d}"

            if is_valid_suffix(suffix_start) and is_valid_suffix(suffix_end):
                start_ord = suffix_to_order(suffix_start)
                end_ord = suffix_to_order(suffix_end)
                if start_ord <= end_ord:
                    rolls = []
                    fixed_prefix = prefix_start.upper()
                    for o in range(start_ord, end_ord + 1):
                        rolls.append(fixed_prefix + order_to_suffix(o))
                    return rolls

    m_start = re.match(r'^(.*?)(\d+)$', start)
    m_end = re.match(r'^(.*?)(\d+)$', end)

    if not m_start or not m_end:
        return [start] if start == end else [start, end]

    prefix_start, num_start = m_start.groups()
    prefix_end, num_end = m_end.groups()

    if prefix_start != prefix_end:
        return [start, end]

    start_n = int(num_start)
    end_n = int(num_end)
    width = len(num_start)

    if start_n > end_n:
        return [start.upper()]

    rolls = []
    for i in range(start_n, end_n + 1):
        rolls.append(f"{prefix_start.upper()}{str(i).zfill(width)}")
    return rolls

def update_excel_com_batch(file_path, student_data, exam_type):
    """
    student_data: List of dicts with keys: 'roll_no', 'marks_map' (dict of q_num->mark), 'is_absent' (bool)
    """
    pythoncom.CoInitialize()
    try:
        excel = win32com.client.DispatchEx("Excel.Application")
    except Exception:
        excel = win32com.client.Dispatch("Excel.Application")
        
    excel.Visible = False
    excel.DisplayAlerts = False
    
    wb = None
    try:
        unblock_file(file_path)
        try:
            wb = excel.Workbooks.Open(file_path)
        except Exception as e:
            raise Exception(f"Failed to open Excel file via COM: {str(e)}")
            
        if wb is None:
            raise Exception("Excel returned None.")
        
        # Find Sheet
        ws = None
        for i in range(1, wb.Sheets.Count + 1):
            sheet = wb.Sheets(i)
            if sheet.Name == exam_type:
                ws = sheet
                break
        
        if not ws:
            for i in range(1, wb.Sheets.Count + 1):
                sheet = wb.Sheets(i)
                if "objective" in sheet.Name.lower() and exam_type.split('-')[1] in sheet.Name:
                    ws = sheet
                    break
        
        if not ws:
            ws = wb.ActiveSheet
            print(f"Warning: Sheet {exam_type} not found. Using active sheet: {ws.Name}")
        else:
            print(f"Updating sheet: {ws.Name}")
            
        # Unprotect Sheet
        try:
            if ws.ProtectContents:
                ws.Unprotect()
        except Exception as e:
            print(f"Warning: Failed to unprotect sheet: {e}")
        
        # Find Columns
        roll_no_col = None
        header_row = None
        q_cols = {}
        total_col = None
        
        used_range = ws.UsedRange
        max_row = used_range.Rows.Count + used_range.Row - 1
        max_col = used_range.Columns.Count + used_range.Column - 1
        rows_to_scan = min(max_row, 30)
        
        for r in range(1, rows_to_scan + 1):
            for c in range(1, max_col + 1):
                val = ws.Cells(r, c).Value
                if not val:
                    continue
                val_str = str(val).strip()
                
                if re.search(r'(?i)\broll\s*no\b', val_str):
                    roll_no_col = c
                    header_row = r
                
                if re.search(r'(?i)objective\s+total', val_str):
                    total_col = c
                
                m = re.search(r'(?i)(?:^|\b)(?:Q|Question\s*No\.?)\s*(\d+)\b', val_str)
                if m:
                    q_num = int(m.group(1))
                    q_cols[q_num] = c
        
        if not roll_no_col:
            raise Exception("Could not find 'Roll No' column")
            
        start_row = header_row + 1 if header_row else 1
        
        # Process each student
        # We need to find the NEXT EMPTY ROW for each student, OR match existing.
        # Strategy: 
        # 1. Map existing Roll Nos in Excel to Row Numbers.
        # 2. Find the first empty row after the header (or after last data).
        
        existing_rolls = {}
        first_empty_row = -1
        
        # Scan current rows
        # Limit scan to reasonable number if file is huge, or used_range
        # But we might need to append.
        
        # Let's scan UsedRange first
        for r in range(start_row, max_row + 1):
            val = ws.Cells(r, roll_no_col).Value
            if val:
                existing_rolls[str(val).strip().upper()] = r
            else:
                if first_empty_row == -1:
                    first_empty_row = r
        
        if first_empty_row == -1:
            first_empty_row = max_row + 1
            
        current_write_row = first_empty_row
        
        for student in student_data:
            roll = student['roll_no']
            marks_map = student['marks_map']
            is_absent = student['is_absent']
            
            # Determine Row
            if roll in existing_rolls:
                target_row = existing_rolls[roll]
            else:
                # Use next empty row
                target_row = current_write_row
                current_write_row += 1
                
                # Write Roll No
                cell = ws.Cells(target_row, roll_no_col)
                if not (ws.ProtectContents and cell.Locked):
                    cell.Value = roll
            
            # Write Marks
            if is_absent:
                # Leave empty
                for q_num in range(1, 21):
                    if q_num in q_cols:
                        cell = ws.Cells(target_row, q_cols[q_num])
                        if not (ws.ProtectContents and cell.Locked):
                            cell.Value = "" # Clear cell
                
                # Clear Total as well
                computed_total = ""
            else:
                # Write Marks
                for q_num in range(1, 21):
                    mark = int(marks_map.get(q_num, 0))
                    if q_num in q_cols:
                        cell = ws.Cells(target_row, q_cols[q_num])
                        if not (ws.ProtectContents and cell.Locked):
                            cell.Value = mark
                
                computed_total = sum(int(marks_map.get(i, 0)) for i in range(1, 21))

            # Write Total
            target_total_col = None
            if total_col:
                target_total_col = total_col
            elif q_cols:
                target_total_col = max(q_cols.values()) + 1
                
            if target_total_col:
                cell = ws.Cells(target_row, target_total_col)
                if not (ws.ProtectContents and cell.Locked):
                    cell.Value = computed_total

        wb.Save()
        
    except Exception as e:
        raise e
    finally:
        if wb:
            try:
                wb.Close()
            except:
                pass
        if 'excel' in locals():
            try:
                excel.Quit()
            except:
                pass
        pythoncom.CoUninitialize()

@app.route('/')
def index():
    return render_template('landing.html')

@app.route('/teacher-login', methods=['GET', 'POST'])
def teacher_login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        
        # Check if fields are empty
        if not email or not password:
            return render_template('teacher_login.html', error="Please enter all fields")
        
        # Check credentials
        if email in USERS and USERS[email]['password'] == password and USERS[email]['type'] == 'teacher':
            session['user_id'] = email
            session['user_type'] = 'teacher'
            session['user_name'] = USERS[email]['name']
            return redirect(url_for('teacher'))
        else:
            return render_template('teacher_login.html', error="Invalid email or password")
    
    return render_template('teacher_login.html')

@app.route('/student-login', methods=['GET', 'POST'])
def student_login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Check credentials
        if email in USERS and USERS[email]['password'] == password and USERS[email]['type'] == 'student':
            session['user_id'] = email
            session['user_type'] = 'student'
            session['user_name'] = USERS[email]['name']
            return redirect(url_for('student'))
        else:
            return render_template('student_login.html', error="Invalid email/roll number or password")
    
    return render_template('student_login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/teacher')
def teacher():
    if 'user_type' not in session or session['user_type'] != 'teacher':
        return redirect(url_for('teacher_login'))
    return render_template('teacher_dashboard.html')

@app.route('/paper-generation')
def paper_generation():
    if 'user_type' not in session or session['user_type'] != 'teacher':
        return redirect(url_for('teacher_login'))
    return render_template('generator.html')

@app.route('/paper-correction')
def paper_correction():
    if 'user_type' not in session or session['user_type'] != 'teacher':
        return redirect(url_for('teacher_login'))
    return render_template('index.html')

@app.route('/student')
def student():
    if 'user_type' not in session or session['user_type'] != 'student':
        return redirect(url_for('student_login'))
    return render_template('student.html')


@app.route('/upload', methods=['POST'])
def upload():
    # Only check for image_files
    if 'image_files' not in request.files:
        return "No file part"
    
    try:
        image_files = request.files.getlist('image_files')
        
        # New Inputs
        start_roll_no = request.form.get('start_roll_no', '').strip()
        end_roll_no = request.form.get('end_roll_no', '').strip()
        absentees_str = request.form.get('absentees', '').strip()
        lateral_str = request.form.get('lateral_entries', '').strip()
        exam_type = request.form.get('exam_type', 'Objective-1')
        pages_per_student = int(request.form.get('pages_per_student', 1))
        
        if not start_roll_no or not end_roll_no:
            return "Please provide both Start and End Roll Numbers."
        
        # Parse Absentees
        absentees_set = set()
        if absentees_str:
            parts = [x.strip().upper() for x in absentees_str.split(',')]
            for p in parts:
                if p:
                    absentees_set.add(p)
        
        # Generate Roll Schedule
        all_rolls = generate_roll_numbers(start_roll_no, end_roll_no)
        
        # Append Lateral Entries
        if lateral_str:
            parts = [x.strip().upper() for x in lateral_str.split(',')]
            for p in parts:
                if p and p not in all_rolls:
                    all_rolls.append(p)
        
        # Prepare Student List (Present/Absent)
        # Identify Present Students to map images
        present_rolls = [r for r in all_rolls if r not in absentees_set]
        
        # Filter valid images
        valid_images = [img for img in image_files if img.filename != '']
        
        # If there are present students, we must have images only for them.
        # If everyone is absent, we do NOT require any uploads and will leave marks empty.
        if present_rolls:
            if not valid_images:
                return render_template('index.html', error="Upload answer sheets only for PRESENT students (absentees need no upload).")
            
            # Check expected images (only for present students)
            expected_images = len(present_rolls) * pages_per_student
            
            if expected_images != len(valid_images):
                msg = (
                    f"Expected {expected_images} image(s) for {len(present_rolls)} present "
                    f"student(s) with {pages_per_student} page(s) each, but got {len(valid_images)}."
                )
                return render_template('index.html', error=msg)
        
        # Save Images
        saved_image_paths = []
        for img_file in valid_images:
            img_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(img_file.filename))
            img_file.save(img_path)
            saved_image_paths.append(img_path)
            
        saved_image_paths.sort(key=lambda x: natural_sort_key(os.path.basename(x)))
        
        # ---------------------------------------------------------
        # SMART ASSIGNMENT LOGIC (Filename Match vs Sequential)
        # ---------------------------------------------------------
        assigned_map = {roll: [] for roll in present_rolls}
        unassigned_images = []
        
        # 1. Try to match filenames to Roll Numbers
        for img_path in saved_image_paths:
            filename = os.path.basename(img_path)
            matched_roll = None
            
            # Check against all present rolls
            # Optimization: Sort rolls by length descending to match longest first (though usually fixed length)
            # But straightforward check is fine.
            for roll in present_rolls:
                # Case insensitive check
                if roll.lower() in filename.lower():
                    matched_roll = roll
                    break
            
            if matched_roll:
                assigned_map[matched_roll].append(img_path)
            else:
                unassigned_images.append(img_path)
                
        # 2. Sort assigned images by name (for multi-page safety)
        for roll in assigned_map:
            assigned_map[roll].sort(key=lambda x: natural_sort_key(os.path.basename(x)))

        # ---------------------------------------------------------
        
        # Use Master Template / Existing Result File
        master_template_path = os.path.abspath('master_template.xlsx')
        if not os.path.exists(master_template_path):
             return render_template('index.html', error="Master template not found on server.")

        output_filename = f"updated_marks_{exam_type}.xlsx"
        output_path = os.path.join(app.config['Result_FOLDER'], output_filename)
        
        # If the result file does not exist yet, OR user checked "clear_existing", 
        # create it from the master template.
        clear_existing = request.form.get('clear_existing') == 'on'
        if not os.path.exists(output_path) or clear_existing:
            shutil.copy2(master_template_path, output_path)
        
        # Processing Loop
        student_data = []
        unassigned_idx = 0
        
        for roll in all_rolls:
            data = {
                'roll_no': roll,
                'is_absent': False,
                'marks_map': {}
            }
            
            if roll in absentees_set:
                data['is_absent'] = True
            else:
                # Determine images for this student
                images_to_process = []
                
                # Logic: If explicitly assigned via filename, use those.
                # If not, take from unassigned pool sequentially.
                if assigned_map.get(roll):
                    images_to_process = assigned_map[roll]
                else:
                    # Take next N images from unassigned pool
                    for _ in range(pages_per_student):
                        if unassigned_idx < len(unassigned_images):
                            images_to_process.append(unassigned_images[unassigned_idx])
                            unassigned_idx += 1
                
                if not images_to_process:
                     data['is_absent'] = True
                else:
                    # Process images
                    m_map = {}
                    current_q = 1
                    
                    for img_path in images_to_process:
                        results = process_image(img_path)
                        # Append marks sequentially
                        for res in results:
                            m_map[current_q] = res['mark']
                            current_q += 1
                    
                    data['marks_map'] = m_map
            
            student_data.append(data)
            
        # Update Excel Batch
        update_excel_com_batch(output_path, student_data, exam_type)
        
        return render_template('result.html', 
                               output_file=output_filename,
                               total="Batch Processed")
                               
    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"""
        <html>
        <body style="background-color: white; color: black; padding: 20px; font-family: sans-serif;">
            <h1>Error Processing Files</h1>
            <p>{str(e)}</p>
            <pre style="background: #eee; padding: 10px; border-radius: 5px;">{traceback.format_exc()}</pre>
            <a href="/">Go Back</a>
        </body>
        </html>
        """

@app.route('/download/<filename>')
def download_file(filename):
    return send_file(os.path.join(app.config['Result_FOLDER'], filename), as_attachment=True)

@app.route('/generate', methods=['POST'])
def generate():
    """Generate question paper PDFs"""
    try:
        from generate_paper_logic import generate_question_papers
        import zipfile
        import io
        
        # Generate PDFs
        pdf_files = generate_question_papers(request.form)
        
        # Create ZIP file
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for pdf_file in pdf_files:
                zip_file.write(pdf_file, os.path.basename(pdf_file))
                os.remove(pdf_file)  # Clean up individual PDFs
        
        zip_buffer.seek(0)
        
        return send_file(
            zip_buffer,
            mimetype='application/zip',
            as_attachment=True,
            download_name='Question_Papers.zip'
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"Error generating papers: {str(e)}", 500

if __name__ == '__main__':
    app.run(debug=True)
