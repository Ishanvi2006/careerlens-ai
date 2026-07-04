from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app import db, bcrypt
from app.models import User

auth = Blueprint('auth', __name__)


# ─────────────────────────────────────
# REGISTER
# ─────────────────────────────────────
@auth.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        full_name = request.form.get('full_name')
        email     = request.form.get('email')
        password  = request.form.get('password')
        college   = request.form.get('college')
        branch    = request.form.get('branch')
        semester  = request.form.get('semester')

        # Check if email exists
        existing = User.query.filter_by(email=email).first()
        if existing:
            flash('Email already registered. Please login.', 'danger')
            return redirect(url_for('auth.register'))

        # Hash password
        hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')

        # Create user
        user = User(
            full_name = full_name,
            email     = email,
            password  = hashed_pw,
            college   = college,
            branch    = branch,
            semester  = int(semester) if semester else None
        )
        db.session.add(user)
        db.session.commit()

        flash('Account created! Please login.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html')


# ─────────────────────────────────────
# LOGIN
# ─────────────────────────────────────
@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        email    = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()

        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            flash(f'Welcome back, {user.full_name}!', 'success')

            # Redirect to page they were trying to access
            next_page = request.args.get('next')
            return redirect(next_page or url_for('main.index'))
        else:
            flash('Invalid email or password.', 'danger')

    return render_template('auth/login.html')


# ─────────────────────────────────────
# LOGOUT
# ─────────────────────────────────────
@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))


# ─────────────────────────────────────
# PROFILE
# ─────────────────────────────────────
@auth.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':

        user = User.query.get(current_user.id)

        user.full_name   = request.form.get('full_name')
        user.phone       = request.form.get('phone')
        user.college     = request.form.get('college')
        user.branch      = request.form.get('branch')
        user.target_role = request.form.get('target_role')

        semester = request.form.get('semester')
        if semester:
            user.semester = int(semester)

        try:
            db.session.commit()
            db.session.refresh(user)   # ← ADD THIS LINE
            flash('Profile updated successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'danger')

        return redirect(url_for('auth.profile'))

    # Fetch fresh user from DB on every GET
    user = User.query.get(current_user.id)
    return render_template('auth/profile.html', user=user)