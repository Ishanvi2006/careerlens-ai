from flask import Blueprint, render_template, jsonify, request, current_app
from app.models import Job, Skill, JobSkill
from app import db
from sqlalchemy import func
import os
from werkzeug.utils import secure_filename
from app.ml import analyze_resume, recommend_domains, find_skill_gap

main = Blueprint('main', __name__)


# ─────────────────────────────────────
# HOME — DASHBOARD
# ─────────────────────────────────────
@main.route('/')
def index():
    total_jobs = Job.query.count()
    total_skills = Skill.query.count()
    total_companies = db.session.query(
        func.count(func.distinct(Job.company))
    ).scalar()
    total_domains = db.session.query(
        func.count(func.distinct(Job.domain))
    ).scalar()

    top_skills = db.session.query(
        Skill.name,
        func.count(JobSkill.id).label('demand')
    ).join(JobSkill).group_by(Skill.name)\
     .order_by(func.count(JobSkill.id).desc())\
     .limit(10).all()

    top_companies = db.session.query(
        Job.company,
        func.count(Job.id).label('count')
    ).group_by(Job.company)\
     .order_by(func.count(Job.id).desc())\
     .limit(10).all()

    domain_counts = db.session.query(
        Job.domain,
        func.count(Job.id).label('count')
    ).group_by(Job.domain)\
     .order_by(func.count(Job.id).desc()).all()

    latest_jobs = Job.query\
        .order_by(Job.scraped_at.desc())\
        .limit(10).all()

    return render_template('dashboard.html',
        total_jobs      = total_jobs,
        total_skills    = total_skills,
        total_companies = total_companies,
        total_domains   = total_domains,
        top_skills      = top_skills,
        top_companies   = top_companies,
        domain_counts   = domain_counts,
        latest_jobs     = latest_jobs
    )


# ─────────────────────────────────────
# API — SKILLS DATA
# ─────────────────────────────────────
@main.route('/api/skills')
def api_skills():
    top_skills = db.session.query(
        Skill.name,
        func.count(JobSkill.id).label('demand')
    ).join(JobSkill).group_by(Skill.name)\
     .order_by(func.count(JobSkill.id).desc())\
     .limit(10).all()

    return jsonify({
        'labels': [s.name for s in top_skills],
        'values': [s.demand for s in top_skills]
    })


# ─────────────────────────────────────
# API — DOMAIN DATA
# ─────────────────────────────────────
@main.route('/api/domains')
def api_domains():
    domain_counts = db.session.query(
        Job.domain,
        func.count(Job.id).label('count')
    ).group_by(Job.domain)\
     .order_by(func.count(Job.id).desc()).all()

    return jsonify({
        'labels': [d.domain for d in domain_counts],
        'values': [d.count for d in domain_counts]
    })


# ─────────────────────────────────────
# API — COMPANIES DATA
# ─────────────────────────────────────
@main.route('/api/companies')
def api_companies():
    top_companies = db.session.query(
        Job.company,
        func.count(Job.id).label('count')
    ).group_by(Job.company)\
     .order_by(func.count(Job.id).desc())\
     .limit(10).all()

    return jsonify({
        'labels': [c.company for c in top_companies],
        'values': [c.count for c in top_companies]
    })


# ─────────────────────────────────────
# ALL JOBS PAGE
# ─────────────────────────────────────
@main.route('/jobs')
def jobs():
    domain = request.args.get('domain', '')
    search = request.args.get('search', '')
    page   = request.args.get('page', 1, type=int)

    query = Job.query
    if domain:
        query = query.filter(Job.domain == domain)
    if search:
        query = query.filter(Job.title.ilike(f'%{search}%'))

    jobs = query.order_by(Job.scraped_at.desc())\
                .paginate(page=page, per_page=20)

    domains = db.session.query(Job.domain).distinct().all()

    return render_template('jobs.html',
        jobs           = jobs,
        domains        = domains,
        selected_domain = domain,
        search         = search
    )


# ─────────────────────────────────────
# RESUME UPLOAD PAGE
# ─────────────────────────────────────
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in {'pdf', 'docx'}


@main.route('/resume', methods=['GET', 'POST'])
def resume():
    if request.method == 'POST':
        if 'resume' not in request.files:
            return render_template('resume.html', error='No file uploaded')

        file = request.files['resume']

        if file.filename == '':
            return render_template('resume.html', error='No file selected')

        if not allowed_file(file.filename):
            return render_template('resume.html',
                error='Only PDF and DOCX files allowed')

        filename = secure_filename(file.filename)
        filepath = os.path.join(
            current_app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        result = analyze_resume(filepath, filename)

        if not result:
            return render_template('resume.html',
                error='Could not extract text from resume')

        return render_template('resume_result.html', result=result)

    return render_template('resume.html')


# ─────────────────────────────────────
# DOMAIN RECOMMENDER PAGE
# ─────────────────────────────────────
@main.route('/recommend', methods=['GET', 'POST'])
def recommend():
    if request.method == 'POST':
        skills_input = request.form.get('skills', '')
        user_skills  = [s.strip().lower()
                        for s in skills_input.split(',')
                        if s.strip()]

        if not user_skills:
            return render_template('recommend.html',
                error='Please enter at least one skill')

        recommendations = recommend_domains(user_skills)

        # Top 5 jobs for highest matching domain
        top_domain = recommendations[0]['domain'] \
            if recommendations else None
        jobs_for_top_domain = Job.query\
            .filter_by(domain=top_domain)\
            .limit(5).all() if top_domain else []

        return render_template('recommend.html',
            recommendations     = recommendations,
            user_skills         = user_skills,
            skills_input        = skills_input,
            jobs_for_top_domain = jobs_for_top_domain
        )

    return render_template('recommend.html')


# ─────────────────────────────────────
# SKILL GAP PAGE
# ─────────────────────────────────────
@main.route('/skillgap', methods=['GET', 'POST'])
def skillgap():
    domains = db.session.query(Job.domain).distinct().all()
    domains = [d.domain for d in domains]

    if request.method == 'POST':
        skills_input  = request.form.get('skills', '')
        target_domain = request.form.get('domain', '')

        user_skills = [s.strip().lower()
                       for s in skills_input.split(',')
                       if s.strip()]

        matched, missing = find_skill_gap(user_skills, target_domain)

        return render_template('skillgap.html',
            domains       = domains,
            matched       = matched,
            missing       = missing,
            user_skills   = user_skills,
            skills_input  = skills_input,
            target_domain = target_domain
        )

    return render_template('skillgap.html', domains=domains)