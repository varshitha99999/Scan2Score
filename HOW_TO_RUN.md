# How to Run Scan2Score

## ✅ Correct Way to Run the Application

Run the main application from the **Scan2Score** directory:

```bash
cd Scan2Score
python app.py
```

This will start the complete Scan2Score application with:
- ✅ Teacher and Student authentication
- ✅ Paper correction with roll number detection
- ✅ Question paper generation (integrated from question-paper-folder)
- ✅ Student portal for viewing corrected papers
- ✅ All features working together

## ❌ Don't Run This

**DO NOT** run `question-paper-folder/app.py` - this is a standalone app that was integrated into the main application.

## Optional: AI Distractor Generation

If you want to use the AI-powered distractor generation feature for MCQs:

1. Install the Google Generative AI package:
   ```bash
   pip install google-generativeai
   ```

2. Get a Gemini API key from Google AI Studio

3. Update the `GEMINI_API_KEY` variable in `app.py` (line ~730)

If you don't install this package, the question paper generation will still work perfectly - you'll just need to manually enter the wrong options for MCQs instead of using the "✨ Auto Options" button.

## Access the Application

Once running, open your browser and go to:
- **Main Page**: http://localhost:5000
- **Teacher Login**: http://localhost:5000/teacher-login
- **Student Login**: http://localhost:5000/student-login

## Features Available

### For Teachers:
- **Paper Generation**: Create question papers with MCQs, Match the Following, and Fill in the Blanks
- **Paper Correction**: Upload answer sheets and get automated correction with roll number detection
- **Front & Back Support**: Process both sides of answer sheets (20 questions total)

### For Students:
- **View Papers**: Access your corrected answer sheets
- **Download**: Download your corrected papers as images

## Troubleshooting

If you see import errors, make sure you're running the correct file:
- ✅ Run: `Scan2Score/app.py`
- ❌ Don't run: `question-paper-folder/app.py`