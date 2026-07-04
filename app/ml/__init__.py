import fitz                          # PyMuPDF
import docx
import spacy
import re
from collections import Counter
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from app.models import Job, Skill, JobSkill
import numpy as np

# Load spaCy model
nlp = spacy.load('en_core_web_sm')

# ─────────────────────────────────────
# SKILLS MASTER LIST
# ─────────────────────────────────────
SKILLS_DB = [
    # Programming Languages
    'python', 'java', 'javascript', 'c++', 'c#', 'php', 'ruby',
    'swift', 'kotlin', 'golang', 'rust', 'scala', 'r', 'matlab',
    # Web
    'html', 'css', 'react', 'angular', 'vue', 'node.js', 'django',
    'flask', 'fastapi', 'spring boot', 'express',
    # Database
    'sql', 'mysql', 'postgresql', 'mongodb', 'redis', 'sqlite',
    'oracle', 'cassandra', 'elasticsearch',
    # ML/AI
    'machine learning', 'deep learning', 'nlp', 'computer vision',
    'tensorflow', 'keras', 'pytorch', 'scikit-learn', 'pandas',
    'numpy', 'matplotlib', 'seaborn', 'opencv',
    # Cloud & DevOps
    'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'jenkins',
    'git', 'github', 'linux', 'bash', 'terraform', 'ansible',
    # Data
    'tableau', 'power bi', 'excel', 'spark', 'hadoop', 'airflow',
    'data analysis', 'data visualization', 'statistics',
    # Other
    'rest api', 'graphql', 'microservices', 'agile', 'scrum',
    'jira', 'selenium', 'junit', 'postman', 'figma'
]


# ─────────────────────────────────────
# EXTRACT TEXT FROM PDF
# ─────────────────────────────────────
def extract_text_pdf(filepath):
    text = ""
    doc = fitz.open(filepath)
    for page in doc:
        text += page.get_text()
    doc.close()
    return text


# ─────────────────────────────────────
# EXTRACT TEXT FROM DOCX
# ─────────────────────────────────────
def extract_text_docx(filepath):
    doc = docx.Document(filepath)
    text = ""
    for para in doc.paragraphs:
        text += para.text + "\n"
    return text


# ─────────────────────────────────────
# EXTRACT SKILLS FROM TEXT
# ─────────────────────────────────────
def extract_skills(text):
    text_lower = text.lower()
    found_skills = []
    for skill in SKILLS_DB:
        if skill in text_lower:
            found_skills.append(skill)
    return list(set(found_skills))


# ─────────────────────────────────────
# EXTRACT NAME (spaCy NER)
# ─────────────────────────────────────
def extract_name(text):
    doc = nlp(text[:500])    # check first 500 chars
    for ent in doc.ents:
        if ent.label_ == 'PERSON':
            return ent.text
    # Fallback — first line
    first_line = text.strip().split('\n')[0]
    return first_line[:50] if first_line else 'Not Found'


# ─────────────────────────────────────
# EXTRACT EMAIL
# ─────────────────────────────────────
def extract_email(text):
    pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    matches = re.findall(pattern, text)
    return matches[0] if matches else 'Not Found'


# ─────────────────────────────────────
# EXTRACT PHONE
# ─────────────────────────────────────
def extract_phone(text):
    pattern = r'(\+91[\-\s]?)?[6-9]\d{9}'
    matches = re.findall(pattern, text)
    return matches[0] if matches else 'Not Found'


# ─────────────────────────────────────
# DETECT SECTIONS
# ─────────────────────────────────────
def detect_sections(text):
    text_lower = text.lower()
    sections = {
        'education':    any(w in text_lower for w in ['education', 'b.tech', 'bachelor', 'university', 'college', 'cgpa', 'gpa']),
        'experience':   any(w in text_lower for w in ['experience', 'internship', 'worked', 'company', 'organization']),
        'projects':     any(w in text_lower for w in ['project', 'built', 'developed', 'created', 'implemented']),
        'skills':       any(w in text_lower for w in ['skills', 'technologies', 'tools', 'languages']),
        'certifications': any(w in text_lower for w in ['certification', 'certified', 'certificate', 'course']),
        'summary':      any(w in text_lower for w in ['summary', 'objective', 'about', 'profile']),
        'github':       any(w in text_lower for w in ['github', 'gitlab', 'portfolio']),
        'linkedin':     'linkedin' in text_lower,
    }
    return sections


# ─────────────────────────────────────
# CALCULATE ATS SCORE
# ─────────────────────────────────────
def calculate_score(text, skills_found, sections):
    score = 0
    breakdown = {}

    # 1. Skills score (30 points)
    skill_score = min(30, len(skills_found) * 2)
    score += skill_score
    breakdown['Skills Found'] = {
        'score': skill_score, 'max': 30,
        'comment': f'{len(skills_found)} skills detected'
    }

    # 2. Sections score (25 points)
    key_sections = ['education', 'experience', 'projects', 'skills']
    section_score = sum(5 for s in key_sections if sections.get(s)) + \
                    sum(2 for s in ['certifications', 'summary', 'github', 'linkedin'] if sections.get(s))
    section_score = min(25, section_score)
    score += section_score
    breakdown['Resume Sections'] = {
        'score': section_score, 'max': 25,
        'comment': f'{sum(sections.values())}/8 sections found'
    }

    # 3. Content length score (20 points)
    word_count = len(text.split())
    if word_count > 400:
        length_score = 20
        length_comment = f'Good length ({word_count} words)'
    elif word_count > 200:
        length_score = 12
        length_comment = f'Could be longer ({word_count} words)'
    else:
        length_score = 5
        length_comment = f'Too short ({word_count} words)'
    score += length_score
    breakdown['Content Length'] = {
        'score': length_score, 'max': 20,
        'comment': length_comment
    }

    # 4. Contact info score (15 points)
    email = extract_email(text)
    phone = extract_phone(text)
    contact_score = 0
    if email != 'Not Found':  contact_score += 5
    if phone != 'Not Found':  contact_score += 5
    if sections.get('linkedin'): contact_score += 5
    score += contact_score
    breakdown['Contact Info'] = {
        'score': contact_score, 'max': 15,
        'comment': f'Email: {"✅" if email != "Not Found" else "❌"}  Phone: {"✅" if phone != "Not Found" else "❌"}  LinkedIn: {"✅" if sections.get("linkedin") else "❌"}'
    }

    # 5. Keywords score (10 points)
    keywords = ['achievement', 'improved', 'developed', 'built',
                'led', 'managed', 'designed', 'implemented',
                'reduced', 'increased', 'optimized']
    kw_found = sum(1 for kw in keywords if kw in text.lower())
    kw_score = min(10, kw_found * 2)
    score += kw_score
    breakdown['Action Keywords'] = {
        'score': kw_score, 'max': 10,
        'comment': f'{kw_found} action words found'
    }

    return score, breakdown


# ─────────────────────────────────────
# GENERATE IMPROVEMENT SUGGESTIONS
# ─────────────────────────────────────
def get_suggestions(sections, skills_found, score):
    suggestions = []

    if not sections.get('summary'):
        suggestions.append({
            'type': 'warning',
            'text': 'Add a professional Summary/Objective section at the top'
        })
    if not sections.get('github'):
        suggestions.append({
            'type': 'warning',
            'text': 'Add your GitHub profile link to showcase your projects'
        })
    if not sections.get('linkedin'):
        suggestions.append({
            'type': 'warning',
            'text': 'Add your LinkedIn profile URL for better ATS compatibility'
        })
    if not sections.get('certifications'):
        suggestions.append({
            'type': 'info',
            'text': 'Add certifications (Coursera, NPTEL) to boost credibility'
        })
    if len(skills_found) < 8:
        suggestions.append({
            'type': 'danger',
            'text': f'Only {len(skills_found)} skills detected — add more relevant technical skills'
        })
    if not sections.get('experience'):
        suggestions.append({
            'type': 'danger',
            'text': 'No internship/experience section found — add any projects or internships'
        })
    if score >= 75:
        suggestions.append({
            'type': 'success',
            'text': 'Strong resume! Focus on quantifying your achievements (e.g. "Reduced load time by 30%")'
        })

    return suggestions


# ─────────────────────────────────────
# MAIN ANALYZER FUNCTION
# ─────────────────────────────────────
def analyze_resume(filepath, filename):
    # Extract text
    if filename.endswith('.pdf'):
        text = extract_text_pdf(filepath)
    else:
        text = extract_text_docx(filepath)

    if not text.strip():
        return None

    # Analyze
    name         = extract_name(text)
    email        = extract_email(text)
    phone        = extract_phone(text)
    skills       = extract_skills(text)
    sections     = detect_sections(text)
    score, breakdown = calculate_score(text, skills, sections)
    suggestions  = get_suggestions(sections, skills, score)

    return {
        'name':        name,
        'email':       email,
        'phone':       phone,
        'skills':      skills,
        'sections':    sections,
        'score':       score,
        'breakdown':   breakdown,
        'suggestions': suggestions,
        'word_count':  len(text.split())
    }



# ─────────────────────────────────────
# DOMAIN RECOMMENDER
# ─────────────────────────────────────
def recommend_domains(user_skills):
    """
    Compare user skills against each job domain
    using TF-IDF + Cosine Similarity
    Returns top 5 matching domains with scores
    """

    if not user_skills:
        return []

    # Get all domains from DB
    from app import db
    from sqlalchemy import func

    domains = db.session.query(Job.domain).distinct().all()
    domains = [d.domain for d in domains]

    if not domains:
        return []

    # Build domain skill profiles
    # For each domain → collect all skills required
    domain_profiles = {}
    for domain in domains:
        jobs = Job.query.filter_by(domain=domain).all()
        domain_skills = []
        for job in jobs:
            for js in job.skills:
                domain_skills.append(js.skill.name)
        domain_profiles[domain] = ' '.join(domain_skills)

    # User skill string
    user_profile = ' '.join(user_skills)

    # TF-IDF Vectorization
    all_profiles = list(domain_profiles.values()) + [user_profile]
    vectorizer  = TfidfVectorizer()

    try:
        tfidf_matrix = vectorizer.fit_transform(all_profiles)
    except Exception:
        return []

    # Cosine similarity between user and each domain
    user_vector    = tfidf_matrix[-1]       # last entry is user
    domain_vectors = tfidf_matrix[:-1]      # all others are domains

    similarities = cosine_similarity(user_vector, domain_vectors)[0]

    # Build results
    results = []
    for i, domain in enumerate(domains):
        score = round(float(similarities[i]) * 100, 1)

        # Count live jobs for this domain
        job_count = Job.query.filter_by(domain=domain).count()

        # Get top 3 required skills for this domain
        top_skills = db.session.query(
            Skill.name,
            func.count(JobSkill.id).label('count')
        ).join(JobSkill).join(Job)\
         .filter(Job.domain == domain)\
         .group_by(Skill.name)\
         .order_by(func.count(JobSkill.id).desc())\
         .limit(3).all()

        results.append({
            'domain':     domain,
            'score':      score,
            'job_count':  job_count,
            'top_skills': [s.name for s in top_skills]
        })

    # Sort by score descending
    results = sorted(results, key=lambda x: x['score'], reverse=True)

    return results[:5]     # return top 5


# ─────────────────────────────────────
# SKILL GAP FINDER
# ─────────────────────────────────────
def find_skill_gap(user_skills, target_domain):
    """
    Compare user skills vs what target domain requires
    Returns missing skills ranked by market demand
    """
    from app import db
    from sqlalchemy import func

    if not target_domain:
        return [], []

    # Get all skills required in target domain
    market_skills = db.session.query(
        Skill.name,
        func.count(JobSkill.id).label('demand')
    ).join(JobSkill).join(Job)\
     .filter(Job.domain == target_domain)\
     .group_by(Skill.name)\
     .order_by(func.count(JobSkill.id).desc())\
     .all()

    total_jobs = Job.query.filter_by(domain=target_domain).count()

    user_skills_lower = [s.lower() for s in user_skills]

    matched  = []
    missing  = []

    for skill in market_skills:
        percentage = round((skill.demand / total_jobs) * 100)
        entry = {
            'name':       skill.name,
            'demand':     skill.demand,
            'percentage': percentage
        }
        if skill.name.lower() in user_skills_lower:
            matched.append(entry)
        else:
            missing.append(entry)

    return matched, missing