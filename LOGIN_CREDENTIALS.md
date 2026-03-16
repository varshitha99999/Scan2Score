# Scan2Score - Login Credentials

## Application URL
**http://127.0.0.1:5000**

---

## Teacher Login Credentials

### Primary Credentials:
- **Email:** teacher@college.com
- **Password:** teacher123

### Alternative Options:
- **Username:** teacher
- **Password:** teacher123

- **Username:** admin
- **Password:** admin123

- **Email:** faculty@scan2score.com
- **Password:** faculty123

---

## Student Login Credentials

### Option 1:
- **Email:** student@scan2score.com
- **Password:** student123

### Option 2:
- **Username:** student
- **Password:** student123

### Option 3:
- **Roll Number:** 24WH1A0501
- **Password:** student123

---

## Navigation Flow

### For Teachers:
1. Go to http://127.0.0.1:5000
2. Click on "Teacher Login" card
3. Enter email: **teacher@college.com** and password: **teacher123**
4. Access Teacher Dashboard with two options:
   - **Paper Generation** - Create question papers with MCQs, Match the Following, and Fill in the Blanks
   - **Paper Correction** - Process answer sheets and update marks

### For Students:
1. Go to http://127.0.0.1:5000
2. Click on "Student Login" card
3. Enter email/roll number and password
4. Access Student Portal (currently showing "Coming Soon")

---

## Validation Rules

### Teacher Login:
- If email or password is empty → shows "Please enter all fields"
- If credentials are wrong → shows "Invalid email or password"
- On successful login → redirects to teacher-dashboard.html

### Student Login:
- Similar validation applies for student login

---

## Features

### Teacher Features:
- Generate multiple sets of question papers (PDF format)
- Shuffle questions and options for different sets
- Process scanned answer sheets
- Automatic marks entry to Excel
- Red ink detection
- Batch processing

### Student Features:
- View marks (Coming Soon)
- Track academic progress (Coming Soon)

---

## Notes:
- All passwords are for demonstration purposes only
- In production, use secure password hashing
- Session management is implemented for secure access
- Protected routes require authentication
