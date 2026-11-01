import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from flask import current_app
from database import get_db
from services.security import is_domain_allowed

class EmailService:
    @staticmethod
    def get_smtp_settings(conn=None):
        """Retrieve active SMTP configuration from SQLite system_settings with fallback to app config."""
        if conn is None:
            conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT key, value FROM system_settings WHERE key LIKE 'smtp_%'")
        settings = dict(cursor.fetchall())

        host = settings.get('smtp_host') or current_app.config.get('SMTP_HOST', '127.0.0.1')
        port = int(settings.get('smtp_port') or current_app.config.get('SMTP_PORT', 1025))
        use_tls = str(settings.get('smtp_use_tls', 'false')).lower() in ('true', '1', 'yes')
        user = settings.get('smtp_user') or current_app.config.get('SMTP_USER', '')
        password = settings.get('smtp_password') or current_app.config.get('SMTP_PASSWORD', '')
        sender_from = settings.get('smtp_from') or current_app.config.get('SMTP_FROM', 'simulation@phishguard.test')
        enabled = str(settings.get('smtp_enabled', 'false')).lower() in ('true', '1', 'yes')

        return {
            'smtp_host': host,
            'smtp_port': port,
            'smtp_use_tls': use_tls,
            'smtp_user': user,
            'smtp_password': password,
            'smtp_from': sender_from,
            'smtp_enabled': enabled
        }

    @staticmethod
    def save_smtp_settings(settings, conn=None):
        """Save updated SMTP configuration into SQLite system_settings."""
        if conn is None:
            conn = get_db()
        cursor = conn.cursor()
        for key in ['smtp_host', 'smtp_port', 'smtp_use_tls', 'smtp_user', 'smtp_password', 'smtp_from', 'smtp_enabled']:
            if key in settings:
                val = str(settings[key])
                cursor.execute("""
                    INSERT INTO system_settings (key, value) VALUES (?, ?)
                    ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """, (key, val))
        conn.commit()

    @staticmethod
    def render_email_content(template_body, participant, tracking_url):
        """Replace placeholders in template with participant data and tracking link."""
        keys = participant.keys()
        first_name = participant['first_name'] if 'first_name' in keys and participant['first_name'] else "Team Member"
        last_name = participant['last_name'] if 'last_name' in keys and participant['last_name'] else ""
        full_name = f"{first_name} {last_name}".strip()
        email = participant['email'] if 'email' in keys else (participant['recipient_email'] if 'recipient_email' in keys else "")
        department = participant['department'] if 'department' in keys else "General"
        
        content = template_body.replace("{{name}}", first_name)
        content = content.replace("{{full_name}}", full_name)
        content = content.replace("{{email}}", email)
        content = content.replace("{{department}}", department)
        content = content.replace("{{tracking_url}}", tracking_url)
        return content

    @staticmethod
    def dispatch_simulation_target(target_id, base_url, conn=None):
        """
        Deliver a simulation email to an authorized target.
        If delivery_mode is 'smtp' and SMTP_ENABLED is True, dispatches to local SMTP.
        Otherwise records delivery safely in SQLite simulation database.
        """
        if conn is None:
            conn = get_db()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT t.id, t.tracking_token, t.campaign_id, t.participant_id,
                   p.email, p.first_name, p.last_name, p.department,
                   tmpl.subject, tmpl.sender_name, tmpl.sender_email, tmpl.body_html,
                   c.delivery_mode, c.name as campaign_name
            FROM campaign_targets t
            JOIN participants p ON t.participant_id = p.id
            JOIN campaigns c ON t.campaign_id = c.id
            JOIN email_templates tmpl ON c.template_id = tmpl.id
            WHERE t.id = ?
        """, (target_id,))
        row = cursor.fetchone()
        if not row:
            return False, "Target record not found."

        # Server-side domain allowlist verification
        if not is_domain_allowed(row['email'], conn):
            return False, f"Refused dispatch: Recipient domain for '{row['email']}' is not on the authorized allowlist."

        tracking_url = f"{base_url.rstrip('/')}/simulate/click/{row['tracking_token']}"
        body_html = EmailService.render_email_content(row['body_html'], row, tracking_url)
        
        # Check if actual local SMTP delivery is requested
        smtp_cfg = EmailService.get_smtp_settings(conn)
        is_smtp_active = row['delivery_mode'] == 'smtp' and smtp_cfg['smtp_enabled']

        if is_smtp_active:
            success, err = EmailService._send_via_smtp(
                to_email=row['email'],
                from_email=row['sender_email'],
                from_name=row['sender_name'],
                subject=row['subject'],
                html_content=body_html,
                cfg=smtp_cfg
            )
            if not success:
                return False, f"SMTP Delivery Failed: {err}"

        # Record successful dispatch in database
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute("""
            UPDATE campaign_targets
            SET status = 'Delivered', sent_at = ?
            WHERE id = ?
        """, (now, target_id))

        delivery_source = "Local Mailpit SMTP" if is_smtp_active else "Synthetic Simulation Engine"
        cursor.execute("""
            INSERT INTO interaction_events (campaign_id, participant_id, target_id, event_type, details, created_at)
            VALUES (?, ?, ?, 'simulated_delivery', ?, ?)
        """, (row['campaign_id'], row['participant_id'], target_id, f"Dispatched via {delivery_source}", now))

        conn.commit()
        return True, "Successfully dispatched."

    @staticmethod
    def _send_via_smtp(to_email, from_email, from_name, subject, html_content, cfg=None):
        """Send via local SMTP server (e.g. Mailpit at 127.0.0.1:1025)."""
        if cfg is None:
            cfg = EmailService.get_smtp_settings()

        host = cfg['smtp_host']
        port = cfg['smtp_port']
        user = cfg['smtp_user']
        password = cfg['smtp_password']
        use_tls = cfg['smtp_use_tls']

        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f"{from_name} <{from_email}>"
        msg['To'] = to_email
        msg['X-PhishGuard-Simulation'] = "Authorized-Security-Drill"
        
        part = MIMEText(html_content, 'html')
        msg.attach(part)

        try:
            server = smtplib.SMTP(host, port, timeout=4)
            if use_tls:
                server.starttls()
            if user and password:
                server.login(user, password)
            server.sendmail(from_email, [to_email], msg.as_string())
            server.quit()
            return True, None
        except Exception as e:
            return False, str(e)

    @staticmethod
    def test_smtp_connection(host="127.0.0.1", port=1025, user="", password="", use_tls=False):
        """
        Verify reachability of local SMTP server (Mailpit/Postfix).
        Provides actionable troubleshooting guidance if connection is refused.
        """
        try:
            server = smtplib.SMTP(host, int(port), timeout=3)
            if use_tls:
                server.starttls()
            if user and password:
                server.login(user, password)
            server.quit()
            return True, f"SMTP connection established successfully with {host}:{port}."
        except ConnectionRefusedError:
            return False, (
                f"Connection refused on {host}:{port}. "
                f"Mailpit is not currently running. To use physical email delivery, start Mailpit on port {port}. "
                f"Note: PhishGuard's built-in Simulation Mode is active and runs completely without Mailpit."
            )
        except smtplib.SMTPAuthenticationError:
            return False, f"Authentication failed on {host}:{port}. Please check your SMTP username and password."
        except TimeoutError:
            return False, f"Connection timed out attempting to reach {host}:{port}."
        except Exception as e:
            return False, f"Connection test failed: {str(e)}"
