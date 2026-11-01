from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash, generate_password_hash
from database import get_db

auth_bp = Blueprint('auth', __name__)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id'):
            flash("Please authenticate to access the security administration portal.", "warning")
            return redirect(url_for('auth.login', next=request.url))
        
        # Enforce temporary password change
        if session.get('must_change_password') and request.endpoint not in ('auth.change_password', 'auth.logout'):
            flash("Initial setup requirement: You must change your temporary administrator password before accessing the control lab.", "warning")
            return redirect(url_for('auth.change_password'))
            
        return f(*args, **kwargs)
    return decorated_function

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('user_id'):
        if session.get('must_change_password'):
            return redirect(url_for('auth.change_password'))
        return redirect(url_for('dashboard.overview'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if not username or not password:
            flash("Please enter both administrator username and password.", "danger")
            return render_template('auth/login.html')

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, username, email, password_hash, role,
                   COALESCE(must_change_password, 0) as must_change_password
            FROM users
            WHERE username = ? OR email = ?
        """, (username, username))
        user = cursor.fetchone()

        if user and check_password_hash(user['password_hash'], password):
            csrf = session.get('_csrf_token')
            session.clear()
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            session['must_change_password'] = bool(user['must_change_password'])
            if csrf:
                session['_csrf_token'] = csrf

            if user['must_change_password']:
                flash("Initial setup required: Please establish your new permanent administrator password.", "info")
                return redirect(url_for('auth.change_password'))

            flash(f"Welcome back, {user['username']}. Administrator session initialized securely.", "success")
            next_url = request.args.get('next')
            if next_url and next_url.startswith('/'):
                return redirect(next_url)
            return redirect(url_for('dashboard.overview'))
        else:
            flash("Invalid administrator credentials. Please check your username and password.", "danger")

    return render_template('auth/login.html')

@auth_bp.route('/change-password', methods=['GET', 'POST'])
def change_password():
    """Enforce changing default or temporary administrator password."""
    if not session.get('user_id'):
        flash("Please log in first.", "warning")
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'POST':
        current_password = request.form.get('current_password', '').strip()
        new_password = request.form.get('new_password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()

        cursor.execute("SELECT password_hash FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()

        if not user or not check_password_hash(user['password_hash'], current_password):
            flash("Current password is incorrect.", "danger")
            return render_template('auth/change_password.html')

        if len(new_password) < 8:
            flash("New password must be at least 8 characters in length.", "danger")
            return render_template('auth/change_password.html')

        if new_password != confirm_password:
            flash("New password and confirmation do not match.", "danger")
            return render_template('auth/change_password.html')

        if current_password == new_password:
            flash("New password cannot be identical to your previous temporary password.", "danger")
            return render_template('auth/change_password.html')

        new_hash = generate_password_hash(new_password)
        cursor.execute("""
            UPDATE users
            SET password_hash = ?, must_change_password = 0
            WHERE id = ?
        """, (new_hash, user_id))
        conn.commit()

        session['must_change_password'] = False
        flash("Administrator password updated successfully. Your account is secured.", "success")
        return redirect(url_for('dashboard.overview'))

    return render_template('auth/change_password.html')

@auth_bp.route('/logout', methods=['GET', 'POST'])
def logout():
    session.clear()
    flash("You have been signed out safely.", "info")
    return redirect(url_for('public.landing'))
