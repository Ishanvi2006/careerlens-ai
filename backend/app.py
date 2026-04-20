from flask import Flask, request
import fitz  # PyMuPDF
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

skills_db = [
    "python", "java", "c", "c++", "sql",
    "html", "css", "javascript",
    "react", "node.js",
    "machine learning", "data structures", "algorithms"
]

@app.route('/')
def home():
    return "CareerLens AI Backend Running 🚀"

def extract_text_from_pdf(filepath):
    text = ""
    doc = fitz.open(filepath)

    for page in doc:
        text += page.get_text()

    return text

@app.route('/upload', methods=['POST'])
def upload_resume():
    if 'resume' not in request.files:
        return {"error": "No file uploaded"}, 400

    file = request.files['resume']
    jd_text = request.form.get("job_description", "")

    if file.filename == '':
        return {"error": "Empty filename"}, 400

    file.save(file.filename)

    # Extract resume text
    resume_text = extract_text_from_pdf(file.filename)

    # Extract skills
    resume_skills = extract_skills(resume_text)
    jd_skills = extract_skills(jd_text)

    # Matching logic
    matched = [skill for skill in resume_skills if skill in jd_skills]
    missing = [skill for skill in jd_skills if skill not in resume_skills]

    # Score
    if len(jd_skills) == 0:
        score = 0
    else:
        score = int((len(matched) / len(jd_skills)) * 100)

    return {
        "match_score": score,
        "matched_skills": matched,
        "missing_skills": missing
    }
def extract_skills(text):
    text = text.lower()
    found_skills = []

    for skill in skills_db:
        if skill in text:
            found_skills.append(skill)

    return found_skills

@app.route('/analyze', methods=['POST'])
def analyze():
    data = request.get_json()

    resume_text = data.get("resume_text", "")
    jd_text = data.get("job_description", "")

    # Extract skills
    resume_skills = extract_skills(resume_text)
    jd_skills = extract_skills(jd_text)

    # Matching logic
    matched = [skill for skill in resume_skills if skill in jd_skills]
    missing = [skill for skill in jd_skills if skill not in resume_skills]

    # Score
    if len(jd_skills) == 0:
        score = 0
    else:
        score = int((len(matched) / len(jd_skills)) * 100)

    return {
        "match_score": score,
        "matched_skills": matched,
        "missing_skills": missing
    }

if __name__ == '__main__':
    app.run(debug=True)