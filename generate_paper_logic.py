import random
import copy
from fpdf import FPDF
import os

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
            
            # Logo - Enhanced path resolution
            logo_path = None
            current_dir = os.getcwd()
            script_dir = os.path.dirname(os.path.abspath(__file__))
            
            # Check multiple possible locations for logo
            possible_logo_paths = [
                # Relative to current working directory
                'static/logo.jpg',
                'static/logo.png',
                'question-paper-folder/static/logo.jpg',
                'question-paper-folder/static/logo.png',
                'logo.jpg',
                'logo.png',
                # Relative to script directory
                os.path.join(script_dir, 'static', 'logo.jpg'),
                os.path.join(script_dir, 'static', 'logo.png'),
                os.path.join(script_dir, 'question-paper-folder', 'static', 'logo.jpg'),
                os.path.join(script_dir, 'question-paper-folder', 'static', 'logo.png'),
                # Absolute paths
                os.path.join(current_dir, 'static', 'logo.jpg'),
                os.path.join(current_dir, 'static', 'logo.png'),
                os.path.join(current_dir, 'question-paper-folder', 'static', 'logo.jpg'),
                os.path.join(current_dir, 'question-paper-folder', 'static', 'logo.png')
            ]
            
            print(f"Current working directory: {current_dir}")
            print(f"Script directory: {script_dir}")
            
            for path in possible_logo_paths:
                if os.path.exists(path):
                    logo_path = path
                    print(f"✓ Logo found at: {path}")
                    break
            
            if not logo_path:
                print("✗ Logo not found in any of the expected locations:")
                for path in possible_logo_paths[:6]:  # Show first 6 paths to avoid clutter
                    exists = os.path.exists(path)
                    print(f"  - {path}: {'EXISTS' if exists else 'NOT FOUND'}")
                print("  ... (and other locations)")
                
            if logo_path:
                try:
                    # Verify file exists and is readable
                    if os.path.isfile(logo_path) and os.access(logo_path, os.R_OK):
                        self.image(logo_path, 20, y_after_top + 2, 25)
                        print(f"✓ Logo successfully added from: {logo_path}")
                    else:
                        print(f"✗ Logo file not accessible: {logo_path}")
                except Exception as e:
                    print(f"✗ Error adding logo from {logo_path}: {e}")
            else:
                print("ℹ No logo will be added to the question paper") 
            
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

def clean_text(text):
    """Clean text for Latin-1 encoding"""
    if not text:
        return ""
    replacements = {
        '\u2013': '-', '\u2014': '-',
        '\u2018': "'", '\u2019': "'",
        '\u201c': '"', '\u201d': '"',
        '\u2212': '-',
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text.encode('latin-1', 'replace').decode('latin-1')

def generate_question_papers(form_data):
    """Generate question paper PDFs based on form data"""
    
    # Extract header data
    header_data = {
        'college_name': clean_text(form_data.get('college_name', '')),
        'exam_name': clean_text(form_data.get('exam_name', '')),
        'sub_code': clean_text(form_data.get('sub_code', '')),
        'sub_name': clean_text(form_data.get('sub_name', '')),
        'branch': clean_text(form_data.get('branch', '')),
        'time_duration': clean_text(form_data.get('time_duration', '')),
        'max_marks': clean_text(form_data.get('max_marks', ''))
    }
    
    num_sets = int(form_data.get('num_sets', 1))
    
    # Marks config
    marks_s1 = float(form_data.get('marks_s1', 0.5))
    marks_s2 = float(form_data.get('marks_s2', 0.5))
    marks_s3 = float(form_data.get('marks_s3', 0.5))
    
    # Collect Questions
    mcq_qs = [clean_text(x) for x in form_data.getlist('mcq_q[]') if x.strip()]
    mcq_cs = [clean_text(x) for x in form_data.getlist('mcq_c[]') if x.strip()]
    mcq_w1s = [clean_text(x) for x in form_data.getlist('mcq_w1[]') if x.strip()]
    mcq_w2s = [clean_text(x) for x in form_data.getlist('mcq_w2[]') if x.strip()]
    mcq_w3s = [clean_text(x) for x in form_data.getlist('mcq_w3[]') if x.strip()]
    
    match_lefts = [clean_text(x) for x in form_data.getlist('match_left[]') if x.strip()]
    match_rights = [clean_text(x) for x in form_data.getlist('match_right[]') if x.strip()]
    
    fill_qs = [clean_text(x) for x in form_data.getlist('fill_q[]') if x.strip()]
    fill_as = [clean_text(x) for x in form_data.getlist('fill_a[]') if x.strip()]
    
    # Build question structures
    mcqs = []
    for i in range(len(mcq_qs)):
        if i < len(mcq_cs) and i < len(mcq_w1s) and i < len(mcq_w2s) and i < len(mcq_w3s):
            mcqs.append({
                'question': mcq_qs[i],
                'correct': mcq_cs[i],
                'options': [mcq_cs[i], mcq_w1s[i], mcq_w2s[i], mcq_w3s[i]]
            })
    
    matches = []
    for i in range(min(len(match_lefts), len(match_rights))):
        if i == 0 or (i > 0 and matches):
            if i == 0:
                matches.append({'pairs': []})
            matches[0]['pairs'].append((match_lefts[i], match_rights[i]))
    
    fills = []
    for i in range(min(len(fill_qs), len(fill_as))):
        fills.append({
            'sentence': fill_qs[i],
            'answer': fill_as[i]
        })
    
    # Generate PDFs
    pdf_files = []
    set_codes = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']
    
    for set_num in range(num_sets):
        header_data['set_code'] = set_codes[set_num % len(set_codes)]
        
        pdf = QuestionPaperPDF(header_data)
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)
        
        # Process MCQs
        current_mcqs = copy.deepcopy(mcqs)
        random.shuffle(current_mcqs)
        
        if current_mcqs:
            pdf.set_font('Times', 'B', 11)
            pdf.cell(0, 6, f"I. Choose the Correct Answer: ({len(current_mcqs)} x {marks_s1} = {len(current_mcqs) * marks_s1})", 0, 1)
            pdf.ln(2)
            
            for idx, q in enumerate(current_mcqs, 1):
                pdf.set_font('Times', '', 10)
                pdf.multi_cell(0, 5, f"{idx}. {q['question']}")
                
                options = q['options'][:]
                random.shuffle(options)
                
                labels = ['A', 'B', 'C', 'D']
                for label, opt in zip(labels, options):
                    pdf.cell(10, 5, f"{label})", 0, 0)
                    pdf.multi_cell(0, 5, opt)
                pdf.ln(2)
        
        # Process Match
        if matches and matches[0]['pairs']:
            pdf.set_font('Times', 'B', 11)
            num_pairs = len(matches[0]['pairs'])
            pdf.cell(0, 6, f"II. Match the Following: ({num_pairs} x {marks_s2} = {num_pairs * marks_s2})", 0, 1)
            pdf.ln(2)
            
            left_side = [p[0] for p in matches[0]['pairs']]
            right_side = [p[1] for p in matches[0]['pairs']]
            random.shuffle(right_side)
            
            pdf.set_font('Times', '', 10)
            for i in range(len(left_side)):
                left_text = f"{chr(65+i)}. {left_side[i]}"
                right_text = f"{i+1}. {right_side[i]}"
                pdf.cell(90, 5, left_text, 0, 0)
                pdf.cell(90, 5, right_text, 0, 1)
            pdf.ln(3)
        
        # Process Fill in the Blanks
        current_fills = copy.deepcopy(fills)
        random.shuffle(current_fills)
        
        if current_fills:
            pdf.set_font('Times', 'B', 11)
            pdf.cell(0, 6, f"III. Fill in the Blanks: ({len(current_fills)} x {marks_s3} = {len(current_fills) * marks_s3})", 0, 1)
            pdf.ln(2)
            
            for idx, q in enumerate(current_fills, 1):
                pdf.set_font('Times', '', 10)
                pdf.multi_cell(0, 5, f"{idx}. {q['sentence']}")
                pdf.cell(0, 5, "   Answer: ____________________", 0, 1)
                pdf.ln(2)
        
        # Save PDF
        filename = f"Question_Paper_Set_{set_codes[set_num % len(set_codes)]}.pdf"
        pdf.output(filename)
        pdf_files.append(filename)
    
    return pdf_files
