import json
from datetime import datetime
from flask import Blueprint, jsonify, request, current_app
from database import get_db
from routes.auth import login_required
from services.analytics_service import AnalyticsService
from services.email_service import EmailService

api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/stats')
def get_stats():
    """Return JSON overview metrics."""
    metrics = AnalyticsService.get_overview_metrics()
    return jsonify(metrics)

@api_bp.route('/charts/trend')
def get_chart_trend():
    """Return timeline data for Chart.js."""
    trend = AnalyticsService.get_timeline_trend()
    return jsonify(trend)

@api_bp.route('/charts/departments')
def get_chart_departments():
    """Return department breakdown for Chart.js."""
    breakdown = AnalyticsService.get_department_breakdown()
    labels = [d['department'] for d in breakdown]
    click_rates = [d['click_rate'] for d in breakdown]
    report_rates = [d['report_rate'] for d in breakdown]
    return jsonify({
        'labels': labels,
        'click_rates': click_rates,
        'report_rates': report_rates
    })

@api_bp.route('/campaigns/<int:campaign_id>/trigger-action', methods=['POST'])
@login_required
def trigger_target_action(campaign_id):
    """
    Developer / Demo convenience endpoint:
    Allows simulating an action (open, click, report, complete training)
    on a target in one click from the UI to demonstrate live telemetry updates!
    """
    target_id = request.form.get('target_id') or request.json.get('target_id')
    action = request.form.get('action') or request.json.get('action')

    if not target_id or not action:
        return jsonify({'success': False, 'error': 'target_id and action required'}), 400

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT t.*, p.id as participant_id, p.email
        FROM campaign_targets t
        JOIN participants p ON t.participant_id = p.id
        WHERE t.id = ? AND t.campaign_id = ?
    """, (target_id, campaign_id))
    target = cursor.fetchone()

    if not target:
        return jsonify({'success': False, 'error': 'Target not found'}), 404

    now = datetime.now()

    if action == 'open':
        cursor.execute("UPDATE campaign_targets SET status = 'Opened', opened_at = ? WHERE id = ?", (now, target_id))
        cursor.execute("INSERT INTO interaction_events (campaign_id, participant_id, target_id, event_type, details, created_at) VALUES (?, ?, ?, 'email_preview', 'Simulated via demo trigger', ?)", (campaign_id, target['participant_id'], target_id, now))
    elif action == 'click':
        cursor.execute("UPDATE campaign_targets SET status = 'Clicked', clicked_at = COALESCE(clicked_at, ?) WHERE id = ?", (now, target_id))
        cursor.execute("INSERT INTO interaction_events (campaign_id, participant_id, target_id, event_type, details, created_at) VALUES (?, ?, ?, 'link_clicked', 'Simulated via demo trigger', ?)", (campaign_id, target['participant_id'], target_id, now))
    elif action == 'report':
        cursor.execute("UPDATE campaign_targets SET status = 'Reported', reported_at = ? WHERE id = ?", (now, target_id))
        cursor.execute("INSERT INTO interaction_events (campaign_id, participant_id, target_id, event_type, details, created_at) VALUES (?, ?, ?, 'phish_reported', 'Simulated via demo trigger', ?)", (campaign_id, target['participant_id'], target_id, now))
    elif action == 'train':
        cursor.execute("UPDATE campaign_targets SET status = 'Completed Training', trained_at = ?, quiz_score = 100 WHERE id = ?", (now, target_id))
        cursor.execute("INSERT INTO interaction_events (campaign_id, participant_id, target_id, event_type, details, created_at) VALUES (?, ?, ?, 'quiz_completed', '{\"score\": 100}', ?)", (campaign_id, target['participant_id'], target_id, now))
    else:
        return jsonify({'success': False, 'error': f"Unknown action '{action}'"}), 400

    conn.commit()
    return jsonify({'success': True, 'action': action, 'target_id': target_id, 'new_status': action.capitalize()})

@api_bp.route('/smtp/test', methods=['POST'])
@login_required
def test_smtp():
    """Test reachability of local SMTP server (e.g. Mailpit/Postfix)."""
    data = request.get_json() or request.form
    host = data.get('host', 'localhost')
    port = int(data.get('port', 1025))
    user = data.get('user', '')
    password = data.get('password', '')
    use_tls = str(data.get('use_tls', 'false')).lower() in ('true', '1')

    success, message = EmailService.test_smtp_connection(host, port, user, password, use_tls)
    return jsonify({'success': success, 'message': message})
