import re
import secrets
from flask import session, request, abort, current_app
from database import get_db

def generate_csrf_token():
    """Generate or retrieve a CSRF token for the active session."""
    if '_csrf_token' not in session:
        session['_csrf_token'] = secrets.token_hex(24)
    return session['_csrf_token']

def validate_csrf():
    """Verify the CSRF token in POST/PUT/DELETE requests."""
    if request.method in ('POST', 'PUT', 'DELETE', 'PATCH'):
        # Allow simulation and participant quiz endpoints to be CSRF-free
        if (request.path.startswith('/simulate/') or 
            request.path.startswith('/api/simulation/') or 
            request.path.startswith('/training/')):
            return
        token = request.form.get('csrf_token') or request.headers.get('X-CSRF-Token')
        if not token or token != session.get('_csrf_token'):
            abort(400, description="Invalid or missing CSRF token.")

def is_domain_allowed(email, conn=None):
    """
    Verify whether the recipient email's domain belongs to an authorized allowlist.
    Prevents simulated phishing emails from ever escaping designated test domains.
    """
    if not current_app.config.get('STRICT_ALLOWLIST', True):
        return True

    if not email or '@' not in email:
        return False

    domain = email.strip().split('@')[-1].lower()
    
    close_after = False
    if conn is None:
        conn = get_db()
    
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM allowlist_domains WHERE LOWER(domain) = ? AND is_active = 1", (domain,))
    count = cursor.fetchone()[0]
    
    return count > 0

def sanitize_text(text):
    """Basic text sanitization."""
    if not text:
        return ""
    return str(text).strip()

def is_valid_email(email):
    """Validate standard email pattern."""
    if not email:
        return False
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return re.match(pattern, email.strip()) is not None
