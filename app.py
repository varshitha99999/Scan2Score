import os
import random
import zipfile
import io
import google.generativeai as genai
from flask import Flask, render_template, request, send_file, jsonify, redirect, url_for, session
from fpdf import FPDF

import time
import re

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Dummy User Database
users = {
    'admin': {'password': 'password123', 'type': 'faculty', 'name': 'Faculty Admin'},
    'student': {'password': 'password123', 'type': 'student', 'name': 'Student User'},
    'faculty@scan2score.com': {'password': 'password123', 'type': 'faculty', 'name': 'Faculty Member'},
    'student@scan2score.com': {'password': 'password123', 'type': 'student', 'name': 'Student Name'}
}

# Replace with your actual Gemini API Key
GEMINI_API_KEY = "AIzaSyCt18FQy9jkHYwbmr0dbbAzu-0i4wk4Ilc"

@app.route('/')
def index():
    return render_template('landing.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role') # Hidden field
        
        # Simple check (In real app, query DB)
        if username in users and users[username]['password'] == password:
            # Check if user type matches (optional validation)
            if role and users[username]['type'] != role:
                 return render_template('login.html', error="Invalid User Type for this account")

            session['user_id'] = username
            session['user_type'] = users[username]['type']
            session['user_name'] = users[username]['name']
            
            if users[username]['type'] == 'faculty':
                return redirect(url_for('generate_paper_page'))
            else:
                return redirect(url_for('student_dashboard'))
        else:
            return render_template('login.html', error="Invalid Credentials")
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/generate_paper')
def generate_paper_page():
    if 'user_type' not in session or session['user_type'] != 'faculty':
        return redirect(url_for('login'))
    return render_template('generator.html')

@app.route('/marks_entry')
def marks_entry():
    if 'user_type' not in session or session['user_type'] != 'faculty':
        return redirect(url_for('login'))
    return render_template('marks_entry.html')

@app.route('/student_dashboard')
def student_dashboard():
    if 'user_type' not in session or session['user_type'] != 'student':
        return redirect(url_for('login'))
    return render_template('student_dashboard.html')

@app.route('/api/generate_distractors', methods=['POST'])
def generate_distractors():
    data = request.json
    question = data.get('question')
    correct_answer = data.get('correct_answer')
    
    if not GEMINI_API_KEY or GEMINI_API_KEY == "YOUR_GEMINI_API_KEY_HERE":
        return jsonify({'error': 'Backend API Key not configured'}), 500

    genai.configure(api_key=GEMINI_API_KEY)
    
    # List of models to try in order of preference/quota availability
    # Updated based on available models and error reports
    models_to_try = [
        'gemini-3-flash-preview',
        'gemini-3-pro-preview',
        'gemini-2.0-flash-lite',
        'gemini-2.0-flash-lite-preview-02-05',
        'gemini-2.5-flash-lite',
        'gemini-flash-lite-latest',
        'gemini-pro-latest',
        'gemini-2.0-flash-001',
        'gemini-2.0-flash-lite-001',
        'gemini-2.5-flash',
        'gemini-2.0-flash',
        'gemini-2.5-pro',
        'gemini-exp-1206',
    ]
    
    prompt = ""
    if correct_answer:
        prompt = f"""
        Generate 3 plausible but incorrect options (distractors) for the following multiple choice question.
        Question: {question}
        Correct Answer: {correct_answer}
        
        Return ONLY the 3 distractors separated by pipes (|). Example: Option 1|Option 2|Option 3.
        Do not include any other text.
        """
    else:
        prompt = f"""
        Identify the correct answer for the following multiple choice question and generate 3 plausible incorrect options (distractors).
        Question: {question}
        
        Return the result strictly separated by pipes (|) in this order: Correct Answer|Distractor 1|Distractor 2|Distractor 3.
        Example: Paris|London|Berlin|Madrid
        Do not include any labels or other text.
        """

    all_errors = []
    
    for model_name in models_to_try:
        try:
            print(f"Trying model: {model_name}...")
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            text = response.text.strip()
            parts = text.split('|')
            
            result = {}
            distractors = []
            
            if correct_answer:
                distractors = parts
                while len(distractors) < 3:
                    distractors.append("None of the above")
                result['distractors'] = distractors[:3]
            else:
                if len(parts) >= 1:
                    result['correct_answer'] = parts[0].strip()
                if len(parts) >= 4:
                     distractors = parts[1:4]
                else:
                     distractors = parts[1:]
                
                while len(distractors) < 3:
                    distractors.append("None of the above")
                result['distractors'] = distractors[:3]
            
            print(f"Success with model: {model_name}")
            return jsonify(result)
            
        except Exception as e:
            error_str = str(e)
            print(f"Model {model_name} failed: {error_str}")
            
            # Check for 429 Rate Limit
            if "429" in error_str:
                print(f"Rate limit hit on {model_name}. Switching to next model immediately...")
                # Do NOT sleep here, just try the next model immediately
            
            all_errors.append(f"{model_name}: {error_str}")
            continue
            
    # If all models fail
    return jsonify({'error': f"All models failed. Details: {'; '.join(all_errors)}"}), 500

class QuestionPaperPDF(FPDF):
    def __init__(self, header_data):
        super().__init__()
        self.header_data = header_data
        self.set_margins(20, 20, 20)
        self.set_auto_page_break(True, margin=15)

    def header(self):
        # Top Line (Code/Set) appears on ALL pages
        self.set_font('Times', 'B', 12) 
        self.cell(0, 5, f"Code No: {self.header_data.get('sub_code', '')}", 0, 0, 'L')
        self.cell(0, 5, f"Set No. {self.header_data.get('set_no', '1')}", 0, 1, 'R')
        
        # Only print full college details on Page 1
        if self.page_no() == 1:
            # Save Y position after top line
            y_after_top = self.get_y()
            
            # Logo
            logo_path = None
            if os.path.exists('static/logo.png'): logo_path = 'static/logo.png'
            elif os.path.exists('static/logo.jpg'): logo_path = 'static/logo.jpg'
                
            if logo_path:
                self.image(logo_path, 20, y_after_top + 2, 25) 
            
            self.set_y(y_after_top + 2) 
            
            self.set_font('Times', 'B', 14)
            self.cell(0, 6, self.header_data.get('college_name', ''), 0, 1, 'C')
            
            self.set_font('Times', '', 11)
            self.cell(0, 5, "(Autonomous)", 0, 1, 'C')
            
            self.set_font('Times', 'B', 11)
            self.cell(0, 5, self.header_data.get('exam_name', ''), 0, 1, 'C')
            
            self.cell(0, 5, self.header_data.get('sub_name', ''), 0, 1, 'C')
            
            if self.header_data.get('branch'):
                 self.cell(0, 5, f"({self.header_data.get('branch')})", 0, 1, 'C')
            
            self.ln(1)
            self.set_font('Times', 'B', 12)
            self.cell(0, 5, "Objective Exam", 0, 1, 'C')
            
            # Ensure we are below the logo
            current_y = self.get_y()
            min_y_below_logo = y_after_top + 28
            if current_y < min_y_below_logo:
                self.set_y(min_y_below_logo)
            else:
                self.ln(5)
            
            # Student Details
            self.set_font('Times', 'B', 11)
            self.set_xy(20, self.get_y())
            self.cell(12, 6, "Name: ", 0, 0)
            self.cell(60, 6, "_" * 35, 0, 0)
            
            ht_label_x = 115
            self.set_xy(ht_label_x, self.get_y())
            self.cell(28, 6, "Hall Ticket No.", 0, 0)
            
            x_boxes = ht_label_x + 28
            y = self.get_y()
            box_w = 4.0
            box_h = 8
            for i in range(10):
                self.rect(x_boxes + (i*box_w), y, box_w, box_h)
            self.ln(10)
            
            self.set_font('Times', 'B', 10)
            self.cell(0, 5, f"Answer All Questions. All Questions Carry Equal Marks. Time: {self.header_data.get('time_duration', '20 Min.')} Marks: {self.header_data.get('max_marks', '10')}.", 0, 1, 'C')
            self.ln(5)
        else:
            # On subsequent pages, just add a little spacing
            self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        if self.page_no() == 1:
            self.cell(0, 10, 'Cont......2', 0, 0, 'R')
        else:
            # Standard page number or nothing on last page if desired
            # self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')
            pass



@app.route('/generate', methods=['POST'])
def generate():
    # Helper to clean text for Latin-1 encoding
    def clean_text(text):
        if not text: return ""
        replacements = {
            '\u2013': '-', '\u2014': '-',
            '\u2018': "'", '\u2019': "'",
            '\u201c': '"', '\u201d': '"',
            '\u2212': '-',
        }
        for k, v in replacements.items():
            text = text.replace(k, v)
        # Force encode/decode to strip any remaining non-latin1 chars
        return text.encode('latin-1', 'replace').decode('latin-1')

    # Collect Form Data
    college_name = clean_text(request.form.get('college_name'))
    exam_name = clean_text(request.form.get('exam_name'))
    sub_code = clean_text(request.form.get('sub_code'))
    sub_name = clean_text(request.form.get('sub_name'))
    branch = clean_text(request.form.get('branch'))
    time_duration = clean_text(request.form.get('time_duration'))
    max_marks = clean_text(request.form.get('max_marks'))
    num_sets = int(request.form.get('num_sets', 1))

    # Marks config
    marks_s1 = float(request.form.get('marks_s1', 0.5))
    marks_s2 = float(request.form.get('marks_s2', 0.5))
    marks_s3 = float(request.form.get('marks_s3', 0.5))

    # Collect Questions
    mcq_qs = [clean_text(x) for x in request.form.getlist('mcq_q[]')]
    mcq_cs = [clean_text(x) for x in request.form.getlist('mcq_c[]')]
    mcq_w1s = [clean_text(x) for x in request.form.getlist('mcq_w1[]')]
    mcq_w2s = [clean_text(x) for x in request.form.getlist('mcq_w2[]')]
    mcq_w3s = [clean_text(x) for x in request.form.getlist('mcq_w3[]')]
    
    match_lefts = [clean_text(x) for x in request.form.getlist('match_left[]')]
    match_rights = [clean_text(x) for x in request.form.getlist('match_right[]')]
    
    fill_qs = [clean_text(x) for x in request.form.getlist('fill_q[]')]
    fill_as = [clean_text(x) for x in request.form.getlist('fill_a[]')]

    # Structure Data
    mcqs = []
    for i in range(len(mcq_qs)):
        if mcq_qs[i].strip():
            mcqs.append({
                'q': mcq_qs[i],
                'correct': mcq_cs[i],
                'options': [mcq_cs[i], mcq_w1s[i], mcq_w2s[i], mcq_w3s[i]]
            })

    matches = []
    for i in range(len(match_lefts)):
        if match_lefts[i].strip():
            matches.append((match_lefts[i], match_rights[i]))

    fills = []
    for i in range(len(fill_qs)):
        if fill_qs[i].strip():
            fills.append({'q': fill_qs[i], 'a': fill_as[i]})

    # Generate Sets
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w') as zf:
        
        # Generate PDFs and Answer Keys per Set
        for set_num in range(1, num_sets + 1):
            key_text = f"ANSWER KEY - SET {set_num}\n{'='*25}\n\n"
            
            header_info = {
                'college_name': college_name,
                'exam_name': exam_name,
                'sub_code': sub_code,
                'sub_name': sub_name,
                'branch': branch,
                'time_duration': time_duration,
                'max_marks': max_marks,
                'set_no': str(set_num)
            }
            
            pdf = QuestionPaperPDF(header_info)
            pdf.alias_nb_pages = '{nb}' 
            pdf.add_page()
            
            # --- SECTION 1: MCQs ---
            if mcqs:
                pdf.set_font('Times', 'B', 12)
                total_s1 = len(mcqs) * marks_s1
                total_str = f"{total_s1:g}M"
                pdf.cell(0, 6, f"I.   Multiple Choice Questions ({len(mcqs)} x {marks_s1} = {total_str})", 0, 1, 'C')
                pdf.ln(2)
                
                curr_mcqs = mcqs.copy()
                random.shuffle(curr_mcqs)
                
                key_text += "SECTION I: MCQs\n"
                
                pdf.set_font('Times', '', 12)
                for idx, q in enumerate(curr_mcqs, 1):
                    # Question Text
                    pdf.multi_cell(0, 5, f"{idx}. {q['q']}")
                    
                    # Options
                    opts = q['options'].copy()
                    random.shuffle(opts)
                    
                    # Find correct answer index to generate key
                    correct_idx = -1
                    try:
                        correct_idx = opts.index(q['correct'])
                    except ValueError:
                        pass # Should not happen
                    
                    correct_char = chr(97 + correct_idx) if correct_idx != -1 else "?"
                    key_text += f"{idx}. {q['q']} -> ({correct_char}) {q['correct']}\n"
                    
                    # Layout Options: (a) ... (b) ... (c) ... (d) ...
                    labels = ['a', 'b', 'c', 'd']
                    
                    y_start = pdf.get_y()
                    x_start = pdf.get_x()
                    
                    # Option A
                    pdf.set_xy(x_start + 5, y_start)
                    pdf.cell(80, 5, f"{labels[0]}) {opts[0]}", 0, 0)
                    
                    # Option B
                    pdf.set_xy(x_start + 90, y_start)
                    pdf.cell(80, 5, f"{labels[1]}) {opts[1]}", 0, 1)
                    
                    # Option C
                    pdf.set_xy(x_start + 5, y_start + 5)
                    pdf.cell(80, 5, f"{labels[2]}) {opts[2]}", 0, 0)
                    
                    # Option D
                    pdf.set_xy(x_start + 90, y_start + 5)
                    pdf.cell(80, 5, f"{labels[3]}) {opts[3]}", 0, 1)
                    
                    # Bracket for answer on the right
                    pdf.set_xy(175, y_start + 2)
                    pdf.cell(15, 5, "[      ]", 0, 0)
                    
                    pdf.set_y(y_start + 12) 
                    pdf.ln(4) # Space after every question

            # --- SECTION 2: Match ---
            if matches:
                pdf.ln(5)
                pdf.set_font('Times', 'B', 12)
                total_s2 = len(matches) * marks_s2
                total_str = f"{total_s2:g}M"
                pdf.cell(0, 6, f"II.   Match the Following ({len(matches)} x {marks_s2} = {total_str})", 0, 1, 'C')
                pdf.ln(2)
                
                curr_matches = matches.copy()
                random.shuffle(curr_matches)
                
                left_items = [m[0] for m in curr_matches]
                right_items_shuffled = [m[1] for m in curr_matches]
                random.shuffle(right_items_shuffled) 
                
                key_text += "\nSECTION II: MATCHING\n"
                
                pdf.set_font('Times', '', 12)
                start_num = len(mcqs) + 1
                
                for i in range(len(matches)):
                    y = pdf.get_y()
                    
                    # Left Side (Question)
                    q_text = left_items[i]
                    correct_ans = curr_matches[i][1]
                    
                    # Find where the correct answer ended up in the shuffled right column
                    ans_idx = -1
                    try:
                        ans_idx = right_items_shuffled.index(correct_ans)
                    except ValueError:
                        pass
                        
                    correct_char = chr(97 + ans_idx) if ans_idx != -1 else "?"
                    key_text += f"{start_num + i}. {q_text} -> ({correct_char}) {correct_ans}\n"
                    
                    # PDF Layout
                    pdf.set_xy(20, y)
                    pdf.cell(10, 6, f"{start_num + i}.", 0, 0)
                    pdf.cell(70, 6, f"{q_text}", 0, 0)
                    
                    # Center Brackets
                    pdf.set_xy(100, y)
                    pdf.cell(15, 6, "[      ]", 0, 0)
                    
                    # Right Side
                    pdf.set_xy(130, y)
                    pdf.cell(10, 6, f"{chr(97+i)})", 0, 0) 
                    pdf.cell(60, 6, f"{right_items_shuffled[i]}", 0, 1)
                    
                    pdf.ln(4)
                
                pdf.ln(5)

            # --- SECTION 3: Fill in Blanks ---
            if fills:
                # Force new page for Section III as per requirement
                pdf.add_page()
                
                pdf.set_font('Times', 'B', 12)
                total_s3 = len(fills) * marks_s3
                total_str = f"{total_s3:g}M"
                pdf.cell(0, 6, f"III.   Fill in the Blanks ({len(fills)} x {marks_s3} = {total_str})", 0, 1, 'C')
                pdf.ln(2)
                
                curr_fills = fills.copy()
                random.shuffle(curr_fills)
                
                key_text += "\nSECTION III: FILL IN BLANKS\n"
                
                pdf.set_font('Times', '', 12)
                start_num = len(mcqs) + len(matches) + 1
                
                for idx, q in enumerate(curr_fills, start_num):
                    key_text += f"{idx}. {q['q']} -> {q['a']}\n"
                    
                    # Smart blank replacement
                    question_text = q['q']
                    answer_text = q['a']
                    
                    # Check if user has already placed a blank (underscores) in the question
                    if '_' in question_text:
                        pass
                    elif answer_text and answer_text.strip():
                        if answer_text.strip().lower() in question_text.lower():
                             pattern = re.compile(re.escape(answer_text.strip()), re.IGNORECASE)
                             question_text = pattern.sub('__________', question_text)
                        else:
                             question_text += " ____________________"
                    else:
                        question_text += " ____________________"
                    
                    pdf.multi_cell(0, 6, f"{idx}. {question_text}")
                    pdf.ln(4) 
            
            # End of paper marker
            pdf.ln(10)
            pdf.cell(0, 5, "-ooOoo-", 0, 1, 'C')

            # Save Answer Key for this Set
            zf.writestr(f"Answer_Key_Set_{set_num}.txt", key_text)

            # Output PDF to Zip
            pdf_bytes = pdf.output(dest='S').encode('latin-1') 
            zf.writestr(f"Question_Paper_Set_{set_num}.pdf", pdf_bytes)

    memory_file.seek(0)
    return send_file(
        memory_file,
        mimetype='application/zip',
        as_attachment=True,
        download_name='Question_Papers_Scan2Score.zip'
    )

if __name__ == '__main__':
    app.run(debug=True, port=8080)
