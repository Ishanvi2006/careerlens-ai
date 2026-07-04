from flask_login import UserMixin
from datetime import datetime
from app import db

# ─────────────────────────────────────
# TABLE 1 — USERS
# ─────────────────────────────────────
class User(db.Model, UserMixin):
    __tablename__ = 'users'

    id            = db.Column(db.Integer, primary_key=True)
    full_name     = db.Column(db.String(100), nullable=False)
    email         = db.Column(db.String(120), unique=True, nullable=False)
    password      = db.Column(db.String(255), nullable=False)
    phone         = db.Column(db.String(15))
    college       = db.Column(db.String(150))
    branch        = db.Column(db.String(100))
    semester      = db.Column(db.Integer)
    resume_path   = db.Column(db.String(255))   # path to uploaded resume
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    skills        = db.relationship('UserSkill', backref='user', lazy=True)
    applications  = db.relationship('Application', backref='user', lazy=True)

    def __repr__(self):
        return f'<User {self.email}>'


# ─────────────────────────────────────
# TABLE 2 — JOBS (scraped postings)
# ─────────────────────────────────────
class Job(db.Model):
    __tablename__ = 'jobs'

    id            = db.Column(db.Integer, primary_key=True)
    title         = db.Column(db.String(200), nullable=False)
    company       = db.Column(db.String(150))
    location      = db.Column(db.String(100))
    salary_min    = db.Column(db.Float)          # in LPA
    salary_max    = db.Column(db.Float)          # in LPA
    experience    = db.Column(db.String(50))     # e.g. "0-2 years"
    description   = db.Column(db.Text)
    portal        = db.Column(db.String(50))     # naukri / linkedin / internshala
    job_url       = db.Column(db.String(500))
    domain        = db.Column(db.String(100))    # Data Analyst, Backend Dev etc.
    scraped_at    = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    skills        = db.relationship('JobSkill', backref='job', lazy=True)
    applications  = db.relationship('Application', backref='job', lazy=True)

    def __repr__(self):
        return f'<Job {self.title} @ {self.company}>'


# ─────────────────────────────────────
# TABLE 3 — SKILLS (master skill list)
# ─────────────────────────────────────
class Skill(db.Model):
    __tablename__ = 'skills'

    id            = db.Column(db.Integer, primary_key=True)
    name          = db.Column(db.String(100), unique=True, nullable=False)
    category      = db.Column(db.String(100))    # e.g. Programming, Database, Cloud

    # Relationships
    jobs          = db.relationship('JobSkill', backref='skill', lazy=True)
    users         = db.relationship('UserSkill', backref='skill', lazy=True)

    def __repr__(self):
        return f'<Skill {self.name}>'


# ─────────────────────────────────────
# TABLE 4 — JOB_SKILLS (job ↔ skill)
# ─────────────────────────────────────
class JobSkill(db.Model):
    __tablename__ = 'job_skills'

    id            = db.Column(db.Integer, primary_key=True)
    job_id        = db.Column(db.Integer, db.ForeignKey('jobs.id'), nullable=False)
    skill_id      = db.Column(db.Integer, db.ForeignKey('skills.id'), nullable=False)

    def __repr__(self):
        return f'<JobSkill job={self.job_id} skill={self.skill_id}>'


# ─────────────────────────────────────
# TABLE 5 — USER_SKILLS (user ↔ skill)
# ─────────────────────────────────────
class UserSkill(db.Model):
    __tablename__ = 'user_skills'

    id            = db.Column(db.Integer, primary_key=True)
    user_id       = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    skill_id      = db.Column(db.Integer, db.ForeignKey('skills.id'), nullable=False)
    proficiency   = db.Column(db.String(50))     # beginner / intermediate / advanced

    def __repr__(self):
        return f'<UserSkill user={self.user_id} skill={self.skill_id}>'


# ─────────────────────────────────────
# TABLE 6 — APPLICATIONS (job tracker)
# ─────────────────────────────────────
class Application(db.Model):
    __tablename__ = 'applications'

    id            = db.Column(db.Integer, primary_key=True)
    user_id       = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    job_id        = db.Column(db.Integer, db.ForeignKey('jobs.id'), nullable=False)
    status        = db.Column(db.String(50), default='Applied')
                  # Applied / Viewed / Interview / Rejected / Offered
    applied_at    = db.Column(db.DateTime, default=datetime.utcnow)
    cover_letter  = db.Column(db.Text)           # AI generated cover letter
    portal        = db.Column(db.String(50))     # where it was applied

    def __repr__(self):
        return f'<Application user={self.user_id} job={self.job_id} status={self.status}>'