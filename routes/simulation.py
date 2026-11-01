import json
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, abort
from database import get_db
from services.email_service import EmailService

simulation_bp = Blueprint('simulation', __name__)

@simulation_bp.route('/simulate/preview/<token>')
def preview_email(token):
    """
    Renders an in-browser simulated corporate email client.
    Allows testing simulated phishing emails safely without needing any external mail client.
    """
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT t.id as target_id, t.tracking_token, t.status, t.campaign_id,
               p.email as recipient_email, p.first_name, p.last_name, p.department,
               tmpl.subject, tmpl.sender_name, tmpl.sender_email, tmpl.body_html,
               tmpl.red_flags, tmpl.difficulty, tmpl.educational_tip,
               c.name as campaign_name
        FROM campaign_targets t
        JOIN participants p ON t.participant_id = p.id
        JOIN campaigns c ON t.campaign_id = c.id
        JOIN email_templates tmpl ON c.template_id = tmpl.id
        WHERE t.tracking_token = ?
    """, (token,))
    target = cursor.fetchone()

    if not target:
        abort(404, description="Simulation token not recognized or expired.")

    # Record email preview event if not yet opened
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    if target['status'] in ('Pending', 'Sent', 'Delivered'):
        cursor.execute("""
            UPDATE campaign_targets
            SET status = 'Opened', opened_at = ?
            WHERE tracking_token = ?
        """, (now, token))

        cursor.execute("""
            INSERT INTO interaction_events (campaign_id, participant_id, target_id, event_type, ip_address, user_agent, created_at)
            VALUES (?, (SELECT participant_id FROM campaign_targets WHERE tracking_token = ?), ?, 'email_preview', ?, ?, ?)
        """, (target['campaign_id'], token, target['target_id'], request.remote_addr, request.user_agent.string, now))
        conn.commit()

    tracking_url = url_for('simulation.record_click', token=token, _external=True)
    rendered_body = EmailService.render_email_content(target['body_html'], target, tracking_url)
    red_flags_list = json.loads(target['red_flags']) if target['red_flags'] else []

    return render_template('simulation/email_view.html',
                           target=target,
                           rendered_body=rendered_body,
                           red_flags_list=red_flags_list,
                           token=token)

@simulation_bp.route('/simulate/click/<token>')
def record_click(token):
    """
    Intercepts the click on a simulated phishing link.
    Records safe telemetry and instantly redirects to the ethical awareness teachable moment.
    NEVER collects passwords or sensitive input.
    """
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT t.id, t.status, t.campaign_id, t.participant_id, p.first_name
        FROM campaign_targets t
        JOIN participants p ON t.participant_id = p.id
        WHERE t.tracking_token = ?
    """, (token,))
    target = cursor.fetchone()

    if not target:
        abort(404, description="Invalid tracking link.")

    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    # Update target status to Clicked if not already reported or trained
    if target['status'] not in ('Reported', 'Completed Training'):
        cursor.execute("""
            UPDATE campaign_targets
            SET status = 'Clicked', clicked_at = COALESCE(clicked_at, ?)
            WHERE tracking_token = ?
        """, (now, token))

        cursor.execute("""
            INSERT INTO interaction_events (campaign_id, participant_id, target_id, event_type, ip_address, user_agent, details, created_at)
            VALUES (?, ?, ?, 'link_clicked', ?, ?, '{"safe_path": "/training/teachable-moment"}', ?)
        """, (target['campaign_id'], target['participant_id'], target['id'], request.remote_addr, request.user_agent.string, now))
        
        # Increase participant risk score slightly
        cursor.execute("""
            UPDATE participants
            SET risk_score = MIN(100, risk_score + 10)
            WHERE id = ?
        """, (target['participant_id'],))
        
        conn.commit()

    return redirect(url_for('simulation.teachable_moment', token=token))

@simulation_bp.route('/simulate/report/<token>', methods=['POST', 'GET'])
def record_report(token):
    """
    Records when a participant spots and reports the simulated phishing message.
    Updates the target status to Reported and rewards positive defensive behavior.
    """
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT t.id, t.status, t.campaign_id, t.participant_id, p.first_name, p.email
        FROM campaign_targets t
        JOIN participants p ON t.participant_id = p.id
        WHERE t.tracking_token = ?
    """, (token,))
    target = cursor.fetchone()

    if not target:
        abort(404, description="Invalid tracking token.")

    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute("""
        UPDATE campaign_targets
        SET status = 'Reported', reported_at = ?
        WHERE tracking_token = ?
    """, (now, token))

    cursor.execute("""
        INSERT INTO interaction_events (campaign_id, participant_id, target_id, event_type, ip_address, user_agent, created_at)
        VALUES (?, ?, ?, 'phish_reported', ?, ?, ?)
    """, (target['campaign_id'], target['participant_id'], target['id'], request.remote_addr, request.user_agent.string, now))

    # Reward participant by lowering risk score
    cursor.execute("""
        UPDATE participants
        SET risk_score = MAX(5, risk_score - 15)
        WHERE id = ?
    """, (target['participant_id'],))

    conn.commit()

    return render_template('simulation/reported_success.html', target=target)

@simulation_bp.route('/training/teachable-moment/<token>')
def teachable_moment(token):
    """
    The core educational experience that immediately follows clicking a simulated link.
    De-escalates anxiety, explains the learning scenario, and highlights indicators.
    """
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT t.id, t.tracking_token, t.status, t.quiz_score,
               p.first_name, p.last_name, p.email, p.department,
               tmpl.name as template_name, tmpl.subject, tmpl.sender_name, tmpl.sender_email,
               tmpl.red_flags, tmpl.educational_tip
        FROM campaign_targets t
        JOIN participants p ON t.participant_id = p.id
        JOIN campaigns c ON t.campaign_id = c.id
        JOIN email_templates tmpl ON c.template_id = tmpl.id
        WHERE t.tracking_token = ?
    """, (token,))
    target = cursor.fetchone()

    if not target:
        abort(404, description="Simulation training record not found.")

    red_flags = json.loads(target['red_flags']) if target['red_flags'] else []

    # Safe educational quiz questions
    quiz_questions = [
        {
            'id': 1,
            'question': "What was the most significant warning sign in this email?",
            'options': [
                "The email was sent during regular business hours",
                "The sender's domain address did not match the official organization domain",
                "The email had a standard professional font",
                "The email addressed me by my first name"
            ],
            'correct': 1,
            'explanation': "Attackers frequently use lookalike or third-party domains that mimic legitimate brands."
        },
        {
            'id': 2,
            'question': "When an email claims your account will expire within hours unless you click a link, what should you do?",
            'options': [
                "Immediately click the button to keep your account active",
                "Forward the email to all colleagues in your department",
                "Navigate independently to your known corporate SSO portal or verify with IT directly",
                "Reply to the sender asking if it is real"
            ],
            'correct': 2,
            'explanation': "Urgency is a psychological trigger used by attackers to provoke hasty decisions. Always verify independently."
        },
        {
            'id': 3,
            'question': "How can you safely preview where a hyperlink really leads before clicking it on desktop?",
            'options': [
                "Hover your cursor over the link without clicking to view the destination URL in the status bar",
                "Click the link quickly and close the browser tab immediately",
                "Right-click and copy the link to paste into a search engine",
                "Double-click the link to check its security certificate"
            ],
            'correct': 0,
            'explanation': "Hovering reveals the actual hyperlinked destination, allowing you to catch deceptive hyperlinks."
        }
    ]

    return render_template('simulation/teachable_moment.html',
                           target=target,
                           red_flags=red_flags,
                           quiz_questions=quiz_questions,
                           token=token)

@simulation_bp.route('/training/quiz-submit/<token>', methods=['POST'])
def submit_quiz(token):
    """
    Evaluates quiz responses and records completion.
    """
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT t.id, t.campaign_id, t.participant_id, p.first_name, p.last_name, p.email
        FROM campaign_targets t
        JOIN participants p ON t.participant_id = p.id
        WHERE t.tracking_token = ?
    """, (token,))
    target = cursor.fetchone()

    if not target:
        abort(404, description="Target session expired.")

    # Answers: Q1: 1, Q2: 2, Q3: 0
    correct_answers = {'q1': '1', 'q2': '2', 'q3': '0'}
    score = 0
    for q_key, correct_val in correct_answers.items():
        if request.form.get(q_key) == correct_val:
            score += 1

    percentage_score = round((score / 3.0) * 100)
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    cursor.execute("""
        UPDATE campaign_targets
        SET status = 'Completed Training', trained_at = ?, quiz_score = ?
        WHERE tracking_token = ?
    """, (now, percentage_score, token))

    cursor.execute("""
        INSERT INTO interaction_events (campaign_id, participant_id, target_id, event_type, details, created_at)
        VALUES (?, ?, ?, 'quiz_completed', ?, ?)
    """, (target['campaign_id'], target['participant_id'], target['id'],
          json.dumps({'score': percentage_score, 'correct_answers': score, 'total': 3}), now))

    # Reward participant for completing training
    cursor.execute("""
        UPDATE participants
        SET risk_score = MAX(5, risk_score - 20)
        WHERE id = ?
    """, (target['participant_id'],))

    conn.commit()

    return render_template('simulation/quiz_complete.html',
                           target=target,
                           score=percentage_score,
                           correct_count=score,
                           token=token)
