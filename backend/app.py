from flask import Flask, request, jsonify
import fitz  # PyMuPDF
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)

# Folder setup
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

skills_db = [
    "python", "java", "c", "c++", "sql",
    "html", "css", "javascript",
    "react", "node.js",
    "machine learning", "data structures", "algorithms"
]

@app.route('/')
def home():
    return "CareerLens AI Backend Running 🚀"


# 🔹 Extract text from PDF
def extract_text_from_pdf(filepath):
    text = ""
    try:
        doc = fitz.open(filepath)
        for page in doc:
            text += page.get_text()
        return text
    except Exception as e:
        return ""


# 🔹 Extract skills
def extract_skills(text):
    text = text.lower()
    found_skills = []

    for skill in skills_db:
        if skill in text:
            found_skills.append(skill)

    return found_skills


# 🔹 Main API (Upload + Analyze)
@app.route('/upload', methods=['POST'])
def upload_resume():
    try:
        if 'resume' not in request.files:
            return jsonify({"success": False, "error": "No file uploaded"}), 400

        file = request.files['resume']
        jd_text = request.form.get("job_description", "")

        if file.filename == '':
            return jsonify({"success": False, "error": "Empty filename"}), 400

        if not jd_text:
            return jsonify({"success": False, "error": "Job description required"}), 400

        # Save file safely
        file_path = os.path.join(UPLOAD_FOLDER, "resume.pdf")
        file.save(file_path)

        # Extract resume text
        resume_text = extract_text_from_pdf(file_path)

        if not resume_text:
            return jsonify({"success": False, "error": "Failed to read PDF"}), 500

        # Extract skills
        resume_skills = extract_skills(resume_text)
        jd_skills = extract_skills(jd_text)

        # Matching logic
        matched = [skill for skill in resume_skills if skill in jd_skills]
        missing = [skill for skill in jd_skills if skill not in resume_skills]

        # Score calculation
        score = int((len(matched) / len(jd_skills)) * 100) if jd_skills else 0

        return jsonify({
            "success": True,
            "data": {
                "match_score": score,
                "matched_skills": matched,
                "missing_skills": missing
            }
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# 🔹 Optional: Text-based analysis API
@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        data = request.get_json()

        resume_text = data.get("resume_text", "")
        jd_text = data.get("job_description", "")

        if not resume_text or not jd_text:
            return jsonify({"success": False, "error": "Both resume_text and job_description required"}), 400

        resume_skills = extract_skills(resume_text)
        jd_skills = extract_skills(jd_text)

        matched = [skill for skill in resume_skills if skill in jd_skills]
        missing = [skill for skill in jd_skills if skill not in resume_skills]

        score = int((len(matched) / len(jd_skills)) * 100) if jd_skills else 0

        return jsonify({
            "success": True,
            "data": {
                "match_score": score,
                "matched_skills": matched,
                "missing_skills": missing
            }
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=False)