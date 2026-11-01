import json
import uuid
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, Response, current_app
from database import get_db
from routes.auth import login_required
from services.analytics_service import AnalyticsService
from services.email_service import EmailService
from services.security import is_domain_allowed, is_valid_email

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

@dashboard_bp.route('/')
@login_required
def overview():
    """Main administrative dashboard overview."""
    metrics = AnalyticsService.get_overview_metrics()
    conn = get_db()
    cursor = conn.cursor()

    # Recent campaigns
    cursor.execute("""
        SELECT c.*, tmpl.name as template_name,
               (SELECT COUNT(*) FROM campaign_targets WHERE campaign_id = c.id) as target_count,
               (SELECT COUNT(*) FROM campaign_targets WHERE campaign_id = c.id AND clicked_at IS NOT NULL) as clicked_count,
               (SELECT COUNT(*) FROM campaign_targets WHERE campaign_id = c.id AND reported_at IS NOT NULL) as reported_count
        FROM campaigns c
        JOIN email_templates tmpl ON c.template_id = tmpl.id
        ORDER BY c.created_at DESC
        LIMIT 5
    """)
    recent_campaigns = cursor.fetchall()

    # Recent safe activity feed
    cursor.execute("""
        SELECT e.event_type, e.created_at, e.details,
               p.first_name, p.last_name, p.department,
               c.name as campaign_name
        FROM interaction_events e
        JOIN participants p ON e.participant_id = p.id
        JOIN campaigns c ON e.campaign_id = c.id
        ORDER BY e.created_at DESC
        LIMIT 8
    """)
    recent_events = cursor.fetchall()

    return render_template('dashboard/overview.html',
                           metrics=metrics,
                           recent_campaigns=recent_campaigns,
                           recent_events=recent_events)

@dashboard_bp.route('/campaigns')
@login_required
def campaigns():
    """List and manage phishing simulation campaigns."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT c.*, tmpl.name as template_name, tmpl.difficulty,
               (SELECT COUNT(*) FROM campaign_targets WHERE campaign_id = c.id) as total_targets,
               (SELECT COUNT(*) FROM campaign_targets WHERE campaign_id = c.id AND opened_at IS NOT NULL) as opened_count,
               (SELECT COUNT(*) FROM campaign_targets WHERE campaign_id = c.id AND clicked_at IS NOT NULL) as clicked_count,
               (SELECT COUNT(*) FROM campaign_targets WHERE campaign_id = c.id AND reported_at IS NOT NULL) as reported_count,
               (SELECT COUNT(*) FROM campaign_targets WHERE campaign_id = c.id AND trained_at IS NOT NULL) as trained_count
        FROM campaigns c
        JOIN email_templates tmpl ON c.template_id = tmpl.id
        ORDER BY c.created_at DESC
    """)
    campaign_list = cursor.fetchall()

    cursor.execute("SELECT id, name, category, difficulty FROM email_templates ORDER BY name ASC")
    templates = cursor.fetchall()

    cursor.execute("SELECT DISTINCT department FROM participants ORDER BY department ASC")
    departments = [r['department'] for r in cursor.fetchall()]

    return render_template('dashboard/campaigns.html',
                           campaigns=campaign_list,
                           templates=templates,
                           departments=departments)

@dashboard_bp.route('/campaigns/new', methods=['POST'])
@login_required
def new_campaign():
    """Create and immediately dispatch a new simulation campaign."""
    name = request.form.get('name', '').strip()
    template_id = request.form.get('template_id')
    department_target = request.form.get('department_target', 'All')
    delivery_mode = request.form.get('delivery_mode', 'simulation')

    if not name or not template_id:
        flash("Campaign name and template selection are required.", "danger")
        return redirect(url_for('dashboard.campaigns'))

    conn = get_db()
    cursor = conn.cursor()

    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute("""
        INSERT INTO campaigns (name, template_id, status, delivery_mode, department_target, started_at, created_at)
        VALUES (?, ?, 'Active', ?, ?, ?, ?)
    """, (name, template_id, delivery_mode, department_target, now, now))
    campaign_id = cursor.lastrowid

    # Select target participants
    if department_target == 'All':
        cursor.execute("SELECT id, email FROM participants WHERE is_authorized = 1")
    else:
        cursor.execute("SELECT id, email FROM participants WHERE is_authorized = 1 AND department = ?", (department_target,))
    participants = cursor.fetchall()

    base_url = request.host_url.rstrip('/')
    dispatched_count = 0

    for p in participants:
        token = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO campaign_targets (campaign_id, participant_id, tracking_token, status, sent_at, created_at)
            VALUES (?, ?, ?, 'Sent', ?, ?)
        """, (campaign_id, p['id'], token, now, now))
        target_id = cursor.lastrowid

        # Dispatch
        EmailService.dispatch_simulation_target(target_id, base_url, conn)
        dispatched_count += 1

    conn.commit()
    flash(f"Campaign '{name}' launched successfully with {dispatched_count} authorized participants.", "success")
    return redirect(url_for('dashboard.campaign_detail', campaign_id=campaign_id))

@dashboard_bp.route('/campaigns/<int:campaign_id>')
@login_required
def campaign_detail(campaign_id):
    """Detailed view and telemetry funnel of an individual campaign."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT c.*, tmpl.name as template_name, tmpl.subject, tmpl.sender_name, tmpl.sender_email,
               tmpl.difficulty, tmpl.category, tmpl.red_flags, tmpl.educational_tip
        FROM campaigns c
        JOIN email_templates tmpl ON c.template_id = tmpl.id
        WHERE c.id = ?
    """, (campaign_id,))
    campaign = cursor.fetchone()

    if not campaign:
        flash("Campaign not found.", "warning")
        return redirect(url_for('dashboard.campaigns'))

    # Targets list
    cursor.execute("""
        SELECT t.*, p.first_name, p.last_name, p.email, p.department, p.risk_score
        FROM campaign_targets t
        JOIN participants p ON t.participant_id = p.id
        WHERE t.campaign_id = ?
        ORDER BY t.id ASC
    """, (campaign_id,))
    targets = cursor.fetchall()

    # Metrics
    total = len(targets)
    opened = sum(1 for t in targets if t['opened_at'])
    clicked = sum(1 for t in targets if t['clicked_at'])
    reported = sum(1 for t in targets if t['reported_at'])
    trained = sum(1 for t in targets if t['trained_at'])

    funnel = {
        'total': total,
        'opened': opened,
        'clicked': clicked,
        'reported': reported,
        'trained': trained,
        'click_rate': round(clicked / total * 100, 1) if total > 0 else 0,
        'report_rate': round(reported / total * 100, 1) if total > 0 else 0,
        'training_rate': round(trained / clicked * 100, 1) if clicked > 0 else 0
    }

    # Interaction audit logs for this campaign
    cursor.execute("""
        SELECT e.*, p.first_name, p.last_name, p.email
        FROM interaction_events e
        JOIN participants p ON e.participant_id = p.id
        WHERE e.campaign_id = ?
        ORDER BY e.created_at DESC
        LIMIT 30
    """, (campaign_id,))
    events = cursor.fetchall()

    return render_template('dashboard/campaign_detail.html',
                           campaign=campaign,
                           targets=targets,
                           funnel=funnel,
                           events=events)

@dashboard_bp.route('/campaigns/<int:campaign_id>/status', methods=['POST'])
@login_required
def update_campaign_status(campaign_id):
    """Toggle campaign status (Pause / Resume / Complete)."""
    status = request.form.get('status')
    if status in ('Active', 'Paused', 'Completed'):
        conn = get_db()
        cursor = conn.cursor()
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S') if status == 'Completed' else None
        cursor.execute("UPDATE campaigns SET status = ?, completed_at = COALESCE(completed_at, ?) WHERE id = ?", (status, now, campaign_id))
        conn.commit()
        flash(f"Campaign status updated to {status}.", "success")
    return redirect(url_for('dashboard.campaign_detail', campaign_id=campaign_id))

@dashboard_bp.route('/templates')
@login_required
def templates():
    """Educational email templates gallery and editor."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT tmpl.*,
               (SELECT COUNT(*) FROM campaigns WHERE template_id = tmpl.id) as usage_count
        FROM email_templates tmpl
        ORDER BY tmpl.id ASC
    """)
    all_templates = cursor.fetchall()
    return render_template('dashboard/templates.html', templates=all_templates)

@dashboard_bp.route('/templates/new', methods=['POST'])
@login_required
def create_template():
    """Create a new educational email template."""
    name = request.form.get('name', '').strip()
    category = request.form.get('category', 'General')
    difficulty = request.form.get('difficulty', 'Medium')
    subject = request.form.get('subject', '').strip()
    sender_name = request.form.get('sender_name', '').strip()
    sender_email = request.form.get('sender_email', '').strip()
    body_html = request.form.get('body_html', '').strip()
    educational_tip = request.form.get('educational_tip', '').strip()
    red_flags_raw = request.form.get('red_flags', '')

    flags_list = [f.strip() for f in red_flags_raw.split('\n') if f.strip()]

    if not name or not subject or not body_html:
        flash("Name, Subject, and Email HTML are required.", "danger")
        return redirect(url_for('dashboard.templates'))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO email_templates (name, category, difficulty, subject, sender_name, sender_email, body_html, red_flags, educational_tip)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (name, category, difficulty, subject, sender_name, sender_email, body_html, json.dumps(flags_list), educational_tip))
    conn.commit()

    flash(f"Template '{name}' created successfully.", "success")
    return redirect(url_for('dashboard.templates'))

@dashboard_bp.route('/participants')
@login_required
def participants():
    """Manage authorized test participants and allowlist domains."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT p.*,
               (SELECT COUNT(*) FROM campaign_targets WHERE participant_id = p.id) as total_drills,
               (SELECT COUNT(*) FROM campaign_targets WHERE participant_id = p.id AND clicked_at IS NOT NULL) as drills_clicked,
               (SELECT COUNT(*) FROM campaign_targets WHERE participant_id = p.id AND reported_at IS NOT NULL) as drills_reported
        FROM participants p
        ORDER BY p.id ASC
    """)
    all_participants = cursor.fetchall()

    cursor.execute("SELECT * FROM allowlist_domains ORDER BY domain ASC")
    allowlist = cursor.fetchall()

    return render_template('dashboard/participants.html',
                           participants=all_participants,
                           allowlist=allowlist)

@dashboard_bp.route('/participants/new', methods=['POST'])
@login_required
def add_participant():
    """Add a new authorized participant with strict domain allowlist verification."""
    first_name = request.form.get('first_name', '').strip()
    last_name = request.form.get('last_name', '').strip()
    email = request.form.get('email', '').strip().lower()
    department = request.form.get('department', 'General').strip()

    if not is_valid_email(email):
        flash("Invalid email format.", "danger")
        return redirect(url_for('dashboard.participants'))

    conn = get_db()
    if not is_domain_allowed(email, conn):
        flash(f"Security Alert: Domain for '{email}' is not on the authorized allowlist. PhishGuard strictly blocks simulations to unauthorized external domains.", "danger")
        return redirect(url_for('dashboard.participants'))

    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO participants (email, first_name, last_name, department, risk_score, is_authorized)
            VALUES (?, ?, ?, ?, 50, 1)
        """, (email, first_name, last_name, department))
        conn.commit()
        flash(f"Participant {first_name} {last_name} ({email}) registered successfully.", "success")
    except Exception as e:
        flash(f"Could not add participant: email may already exist.", "danger")

    return redirect(url_for('dashboard.participants'))

@dashboard_bp.route('/participants/allowlist/add', methods=['POST'])
@login_required
def add_allowlist_domain():
    """Add an approved test domain to the allowlist."""
    domain = request.form.get('domain', '').strip().lower()
    desc = request.form.get('description', '').strip()

    if not domain or '.' not in domain:
        flash("Please enter a valid domain (e.g. company.internal).", "danger")
        return redirect(url_for('dashboard.participants'))

    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO allowlist_domains (domain, description, is_active) VALUES (?, ?, 1)", (domain, desc))
        conn.commit()
        flash(f"Domain '{domain}' added to authorized allowlist.", "success")
    except Exception:
        flash("Domain already in allowlist.", "warning")

    return redirect(url_for('dashboard.participants'))

@dashboard_bp.route('/participants/allowlist/<int:domain_id>/edit', methods=['POST'])
@login_required
def edit_allowlist_domain(domain_id):
    """Update an approved test domain."""
    domain = request.form.get('domain', '').strip().lower()
    description = request.form.get('description', '').strip()

    # Accept DNS-style labels and internal lab domains; reject URLs and paths.
    labels = domain.split('.')
    valid = (
        len(labels) >= 2
        and all(label and len(label) <= 63
                and label[0].isalnum() and label[-1].isalnum()
                and all(ch.isalnum() or ch == '-' for ch in label)
                for label in labels)
    )
    if not valid:
        flash("Please enter a valid domain name (without http://, paths, or @).", "danger")
        return redirect(url_for('dashboard.participants'))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE allowlist_domains SET domain = ?, description = ? WHERE id = ?",
        (domain, description, domain_id)
    )
    if cursor.rowcount:
        try:
            conn.commit()
            flash(f"Approved domain '{domain}' updated.", "success")
        except Exception:
            conn.rollback()
            flash("That domain already exists in the allowlist.", "danger")
    else:
        flash("Approved domain not found.", "warning")
    return redirect(url_for('dashboard.participants'))


@dashboard_bp.route('/participants/allowlist/<int:domain_id>/delete', methods=['POST'])
@login_required
def delete_allowlist_domain(domain_id):
    """Delete an approved test domain."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT domain FROM allowlist_domains WHERE id = ?", (domain_id,))
    record = cursor.fetchone()
    if not record:
        flash("Approved domain not found.", "warning")
        return redirect(url_for('dashboard.participants'))

    cursor.execute("DELETE FROM allowlist_domains WHERE id = ?", (domain_id,))
    conn.commit()
    flash(f"Approved domain '{record['domain']}' deleted from the allowlist.", "success")
    return redirect(url_for('dashboard.participants'))


@dashboard_bp.route('/analytics')
@login_required
def analytics():
    """Deep-dive analytics, resilience curves, and department benchmarking."""
    metrics = AnalyticsService.get_overview_metrics()
    dept_breakdown = AnalyticsService.get_department_breakdown()
    template_stats = AnalyticsService.get_template_effectiveness()

    return render_template('dashboard/analytics.html',
                           metrics=metrics,
                           dept_breakdown=dept_breakdown,
                           template_stats=template_stats)

@dashboard_bp.route('/training')
@login_required
def training():
    """Security awareness curriculum library and educational previews."""
    return render_template('dashboard/training.html')

@dashboard_bp.route('/reports')
@login_required
def reports():
    """Executive Security Awareness Assessment Report."""
    metrics = AnalyticsService.get_overview_metrics()
    dept_breakdown = AnalyticsService.get_department_breakdown()
    template_stats = AnalyticsService.get_template_effectiveness()
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT c.name, c.status, c.started_at, c.completed_at,
               COUNT(t.id) as target_count,
               SUM(CASE WHEN t.clicked_at IS NOT NULL THEN 1 ELSE 0 END) as clicked,
               SUM(CASE WHEN t.reported_at IS NOT NULL THEN 1 ELSE 0 END) as reported
        FROM campaigns c
        LEFT JOIN campaign_targets t ON t.campaign_id = c.id
        GROUP BY c.id
        ORDER BY c.created_at DESC
    """)
    campaign_summaries = cursor.fetchall()

    return render_template('dashboard/reports.html',
                           metrics=metrics,
                           dept_breakdown=dept_breakdown,
                           template_stats=template_stats,
                           campaigns=campaign_summaries,
                           now=datetime.now())

@dashboard_bp.route('/reports/export-csv')
@login_required
def export_csv():
    """Export campaign interaction events as safe audit CSV."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT e.id, e.event_type, e.created_at, e.ip_address,
               p.email, p.department, c.name as campaign_name
        FROM interaction_events e
        JOIN participants p ON e.participant_id = p.id
        JOIN campaigns c ON e.campaign_id = c.id
        ORDER BY e.id DESC
    """)
    rows = cursor.fetchall()

    def generate():
        yield "Event_ID,Timestamp,Event_Type,Participant_Email,Department,Campaign,IP_Address\n"
        for r in rows:
            yield f"{r['id']},{r['created_at']},{r['event_type']},{r['email']},{r['department']},\"{r['campaign_name']}\",{r['ip_address']}\n"

    return Response(generate(), mimetype='text/csv', headers={'Content-Disposition': 'attachment; filename=phishguard_audit_log.csv'})

@dashboard_bp.route('/settings')
@login_required
def settings():
    """System, SMTP, and allowlist security settings."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM allowlist_domains")
    allowlist = cursor.fetchall()

    config_info = {
        'strict_allowlist': current_app.config.get('STRICT_ALLOWLIST', True),
        'smtp_enabled': current_app.config.get('SMTP_ENABLED', False),
        'smtp_host': current_app.config.get('SMTP_HOST', 'localhost'),
        'smtp_port': current_app.config.get('SMTP_PORT', 1025),
        'smtp_user': current_app.config.get('SMTP_USER', ''),
        'smtp_from': current_app.config.get('SMTP_FROM', 'simulation@phishguard.test')
    }

    return render_template('dashboard/settings.html', allowlist=allowlist, config=config_info)
