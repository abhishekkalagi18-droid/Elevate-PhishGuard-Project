import os
import sys
from app import create_app
from database import get_db

def run_smoke_test():
    print("[1/5] Booting PhishGuard application context...")
    app = create_app()
    client = app.test_client()

    print("[2/5] Testing public endpoints...")
    # 1. Landing Page
    res = client.get('/')
    assert res.status_code == 200, f"Landing failed: {res.status_code}"
    assert b"Build Human Resilience Against Phishing." in res.data, "Hero title missing"
    assert b"Launch Training Lab" in res.data, "Primary CTA missing"
    assert b"Demonstration Data Only" in res.data, "Demo label missing"
    print("  [OK] Landing page (200 OK)")

    # 2. Ethical Charter
    res = client.get('/ethical-charter')
    assert res.status_code == 200, f"Ethical charter failed: {res.status_code}"
    assert b"The PhishGuard Ethical Simulation Charter" in res.data
    print("  [OK] Ethical charter (200 OK)")

    # 3. Public APIs
    res = client.get('/api/stats')
    assert res.status_code == 200
    json_stats = res.get_json()
    assert 'resilience_score' in json_stats
    print(f"  [OK] API /api/stats (200 OK - Resilience: {json_stats['resilience_score']}/100)")

    res = client.get('/api/charts/trend')
    assert res.status_code == 200
    print("  [OK] API /api/charts/trend (200 OK)")

    res = client.get('/api/charts/departments')
    assert res.status_code == 200
    print("  [OK] API /api/charts/departments (200 OK)")

    print("[3/5] Testing admin authentication & dashboard views...")
    # 4. Login Form
    client.get('/login')
    with client.session_transaction() as sess:
        csrf = sess.get('_csrf_token')

    login_res = client.post('/login', data={
        'username': 'admin',
        'password': 'PhishGuard2026!',
        'csrf_token': csrf
    }, follow_redirects=True)
    assert login_res.status_code == 200
    assert b"Security Resilience Overview" in login_res.data
    print("  [OK] Admin login & session initialized (200 OK)")

    # 5. Dashboard Views
    dashboard_routes = [
        ('/dashboard/', b"Phish-Prone Click Rate"),
        ('/dashboard/campaigns', b"Active &amp; Historical Drills" if b"Active &amp; Historical Drills" in client.get('/dashboard/campaigns').data else b"Active & Historical Drills"),
        ('/dashboard/templates', b"Template Library"),
        ('/dashboard/participants', b"Authorized Test Cohort"),
        ('/dashboard/analytics', b"Resilience Curve (6-Month Trend)"),
        ('/dashboard/training', b"Constructive Learning Modules"),
        ('/dashboard/reports', b"PhishGuard Enterprise Resilience Report"),
        ('/dashboard/settings', b"Ethical Simulation Guardrails")
    ]

    for route, expected_text in dashboard_routes:
        r = client.get(route)
        assert r.status_code == 200, f"Route {route} returned {r.status_code}"
        assert expected_text in r.data, f"Route {route} missing expected text {expected_text}"
        print(f"  [OK] Dashboard route {route} (200 OK)")

    # 6. CSV Export
    csv_res = client.get('/dashboard/reports/export-csv')
    assert csv_res.status_code == 200
    assert 'text/csv' in csv_res.content_type
    print("  [OK] Audit CSV Export (200 OK)")

    print("[4/5] Testing simulation email flow & teachable moment...")
    with app.app_context():
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT tracking_token, campaign_id, id FROM campaign_targets LIMIT 1")
        target_row = cursor.fetchone()
        test_token = target_row['tracking_token']
        campaign_id = target_row['campaign_id']
        target_id = target_row['id']

    # In-browser simulated email preview
    preview_res = client.get(f'/simulate/preview/{test_token}')
    assert preview_res.status_code == 200
    assert b"Enterprise Webmail" in preview_res.data
    assert b"Report Phishing" in preview_res.data
    print("  [OK] In-browser simulated webmail preview (200 OK)")

    # Click simulated link -> redirects to teachable moment
    click_res = client.get(f'/simulate/click/{test_token}', follow_redirects=True)
    assert click_res.status_code == 200
    assert b"Take a breath" in click_res.data
    assert b"3-Minute Micro-Quiz" in click_res.data
    print("  [OK] Simulated link click intercept & teachable moment (200 OK)")

    # Submit quiz
    quiz_res = client.post(f'/training/quiz-submit/{test_token}', data={
        'q1': '1',
        'q2': '2',
        'q3': '0'
    })
    assert quiz_res.status_code == 200
    assert b"Human Resilience Verified" in quiz_res.data
    assert b"100%" in quiz_res.data
    print("  [OK] Awareness quiz grading & certificate generation (200 OK)")

    # Report phishing action
    rep_res = client.post(f'/simulate/report/{test_token}')
    assert rep_res.status_code == 200
    assert b"Outstanding Reflexes" in rep_res.data
    print("  [OK] 'Report Phishing' defensive detection flow (200 OK)")

    print("[5/5] Testing live demo triggers & local SMTP tester...")
    # Interactive Demo trigger: open, click, report, train
    with client.session_transaction() as sess:
        admin_csrf = sess.get('_csrf_token')

    for action in ['open', 'click', 'report', 'train']:
        trig_res = client.post(f'/api/campaigns/{campaign_id}/trigger-action', json={
            'target_id': target_id,
            'action': action
        }, headers={'X-CSRF-Token': admin_csrf})
        assert trig_res.status_code == 200
        trig_json = trig_res.get_json()
        assert trig_json['success'] is True
        print(f"  [OK] Live simulation trigger '{action}' (200 OK)")

    # Test SMTP tester API
    smtp_res = client.post('/api/smtp/test', json={
        'host': '127.0.0.1',
        'port': 1025
    }, headers={'X-CSRF-Token': admin_csrf})
    assert smtp_res.status_code == 200
    print("  [OK] SMTP reachability API handler (200 OK)")

    print("\n" + "=" * 60)
    print("  ALL 25+ SYSTEM CHECKS AND FLOWS PASSED PERFECTLY!")
    print("=" * 60)

if __name__ == '__main__':
    run_smoke_test()
