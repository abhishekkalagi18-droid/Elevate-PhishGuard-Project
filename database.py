import sqlite3
import json
import uuid
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash
from flask import g, current_app

def get_db(db_path=None):
    """Obtain a SQLite database connection with row factory enabled."""
    if db_path is None:
        if 'db' not in g:
            path = current_app.config['DATABASE_PATH']
            g.db = sqlite3.connect(path)
            g.db.row_factory = sqlite3.Row
            g.db.execute("PRAGMA foreign_keys = ON;")
        return g.db
    else:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

def close_db(e=None):
    """Close the request-bound database connection."""
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db(app=None, db_path=None):
    """Initialize database tables and seed baseline data."""
    if app:
        target_path = app.config['DATABASE_PATH']
    else:
        target_path = db_path
        
    conn = get_db(target_path)
    cursor = conn.cursor()

    # Users Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT DEFAULT 'admin',
        must_change_password BOOLEAN DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Allowlist Domains Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS allowlist_domains (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        domain TEXT UNIQUE NOT NULL,
        description TEXT,
        is_active BOOLEAN DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Test Participants Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS participants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        first_name TEXT NOT NULL,
        last_name TEXT NOT NULL,
        department TEXT NOT NULL,
        risk_score INTEGER DEFAULT 50,
        is_authorized BOOLEAN DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Email Templates Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS email_templates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        difficulty TEXT NOT NULL,
        subject TEXT NOT NULL,
        sender_name TEXT NOT NULL,
        sender_email TEXT NOT NULL,
        body_html TEXT NOT NULL,
        red_flags TEXT NOT NULL,
        educational_tip TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Campaigns Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS campaigns (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        template_id INTEGER NOT NULL REFERENCES email_templates(id),
        status TEXT NOT NULL DEFAULT 'Draft',
        delivery_mode TEXT NOT NULL DEFAULT 'simulation',
        department_target TEXT DEFAULT 'All',
        is_archived BOOLEAN DEFAULT 0,
        archived_at TIMESTAMP,
        scheduled_at TIMESTAMP,
        started_at TIMESTAMP,
        completed_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Campaign Targets Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS campaign_targets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        campaign_id INTEGER NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
        participant_id INTEGER NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
        tracking_token TEXT UNIQUE NOT NULL,
        status TEXT NOT NULL DEFAULT 'Pending',
        sent_at TIMESTAMP,
        opened_at TIMESTAMP,
        clicked_at TIMESTAMP,
        reported_at TIMESTAMP,
        trained_at TIMESTAMP,
        quiz_score INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Interaction Events Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS interaction_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        campaign_id INTEGER NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
        participant_id INTEGER NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
        target_id INTEGER NOT NULL REFERENCES campaign_targets(id) ON DELETE CASCADE,
        event_type TEXT NOT NULL,
        ip_address TEXT,
        user_agent TEXT,
        details TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # System Settings Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS system_settings (
        key TEXT PRIMARY KEY,
        value TEXT
    );
    """)

    conn.commit()
    migrate_db(conn)
    seed_data(conn)
    
    if db_path is not None:
        conn.close()

def migrate_db(conn):
    """Safely apply incremental schema migrations while preserving all existing data."""
    cursor = conn.cursor()

    # 1. users: check for must_change_password column
    cursor.execute("PRAGMA table_info(users)")
    user_cols = [r[1] for r in cursor.fetchall()]
    if 'must_change_password' not in user_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN must_change_password BOOLEAN DEFAULT 0")

    # 2. campaigns: check for is_archived and archived_at
    cursor.execute("PRAGMA table_info(campaigns)")
    camp_cols = [r[1] for r in cursor.fetchall()]
    if 'is_archived' not in camp_cols:
        cursor.execute("ALTER TABLE campaigns ADD COLUMN is_archived BOOLEAN DEFAULT 0")
    if 'archived_at' not in camp_cols:
        cursor.execute("ALTER TABLE campaigns ADD COLUMN archived_at TIMESTAMP")

    # 3. Standardize legacy 'Active' campaign status to 'Running'
    cursor.execute("UPDATE campaigns SET status = 'Running' WHERE status = 'Active'")

    # 4. Initialize system_settings with safe defaults if empty
    default_settings = {
        'smtp_host': '127.0.0.1',
        'smtp_port': '1025',
        'smtp_use_tls': 'false',
        'smtp_user': '',
        'smtp_password': '',
        'smtp_from': 'simulation@phishguard.test',
        'smtp_enabled': 'false',
        'strict_allowlist': 'true'
    }
    for key, val in default_settings.items():
        cursor.execute("INSERT OR IGNORE INTO system_settings (key, value) VALUES (?, ?)", (key, val))

    conn.commit()

def fmt_dt(dt):
    if dt is None:
        return None
    if isinstance(dt, datetime):
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    return str(dt)

def seed_data(conn):
    """Insert initial admin user, allowlist domains, templates, participants, and demo campaigns if empty."""
    import os
    cursor = conn.cursor()

    # 1. Admin User (Secure default loaded from environment or generated)
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        admin_user = os.environ.get('PHISHGUARD_ADMIN_USER', 'admin')
        admin_pass = os.environ.get('PHISHGUARD_ADMIN_PASSWORD', 'PhishGuard2026!')
        admin_hash = generate_password_hash(admin_pass)
        cursor.execute("""
            INSERT INTO users (username, email, password_hash, role, must_change_password)
            VALUES (?, ?, ?, 'admin', 1)
        """, (admin_user, f"{admin_user}@phishguard.test", admin_hash))

    # 2. Allowlist Domains
    cursor.execute("SELECT COUNT(*) FROM allowlist_domains")
    if cursor.fetchone()[0] == 0:
        domains = [
            ("company.internal", "Primary corporate intranet test domain"),
            ("example.com", "Standard RFC 2606 safe documentation domain"),
            ("phishguard.test", "Dedicated ethical security lab domain"),
            ("demo.local", "Local developer sandbox domain")
        ]
        for domain, desc in domains:
            cursor.execute("INSERT INTO allowlist_domains (domain, description) VALUES (?, ?)", (domain, desc))

    # 3. Email Templates (Rich Educational Templates)
    cursor.execute("SELECT COUNT(*) FROM email_templates")
    if cursor.fetchone()[0] == 0:
        templates = [
            (
                "IT Security: Immediate Password Expiration",
                "IT & Security",
                "Medium",
                "ACTION REQUIRED: Your corporate password expires in 4 hours",
                "Corporate IT Support",
                "security-noreply@it-identity-support.co",
                """<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 24px; border: 1px solid #e2e8f0; border-radius: 8px;">
    <div style="border-bottom: 2px solid #ef4444; padding-bottom: 12px; margin-bottom: 20px;">
        <span style="font-size: 18px; font-weight: 700; color: #1e293b;">Enterprise IT Identity Services</span>
    </div>
    <h3 style="color: #dc2626; margin-top: 0;">Urgent: Password Expiration Notice</h3>
    <p>Dear {{name}},</p>
    <p>Your directory access password is set to expire today in accordance with quarterly security protocol ISO-27001.</p>
    <p>To retain uninterrupted access to your enterprise email, VPN, and internal tooling, you must verify your identity and renew your credentials immediately.</p>
    <div style="text-align: center; margin: 30px 0;">
        <a href="{{tracking_url}}" style="background-color: #2563eb; color: #ffffff; padding: 12px 24px; border-radius: 6px; text-decoration: none; font-weight: 600; display: inline-block;">Keep Current Password & Verify</a>
    </div>
    <p style="font-size: 13px; color: #64748b;">If no action is taken within 4 hours, your domain account will be locked and an administrative ticket will be issued.</p>
    <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 24px 0;" />
    <p style="font-size: 11px; color: #94a3b8;">Sent by Global Identity Directory Services • Automated Notification System</p>
</div>""",
                json.dumps([
                    "Lookalike external sender domain (it-identity-support.co vs internal domain)",
                    "Artificial urgency inducing anxiety (4-hour expiration deadline)",
                    "Vague threat of account lockout to force rushed action",
                    "Buttons offering to 'Keep Current Password' contradict genuine IT password changes"
                ]),
                "Always navigate directly to your company's known identity portal or SSO settings. Real IT teams never demand immediate password renewals via email links."
            ),
            (
                "HR Department: Mandatory Benefits Review 2026",
                "Human Resources",
                "Low",
                "Mandatory: Review Updated 2026 Health & Retirement Benefits Selection",
                "People & Culture Team",
                "benefits@corp-rewards-portal.info",
                """<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 24px; border: 1px solid #e2e8f0; border-radius: 8px;">
    <div style="border-bottom: 2px solid #3b82f6; padding-bottom: 12px; margin-bottom: 20px;">
        <span style="font-size: 18px; font-weight: 700; color: #1e293b;">People & Culture Department</span>
    </div>
    <h3>Annual Benefits Enrollment Window Closing</h3>
    <p>Hello {{name}},</p>
    <p>We have updated the company medical, dental, and pension matching scheme for the upcoming fiscal year. All full-time team members are required to confirm their coverage choices.</p>
    <p>Failure to complete the review will revert your plan to the default minimum package.</p>
    <div style="margin: 24px 0;">
        <a href="{{tracking_url}}" style="background-color: #0f172a; color: #ffffff; padding: 12px 24px; border-radius: 6px; text-decoration: none; font-weight: 600; display: inline-block;">View 2026 Benefits Package & Confirm</a>
    </div>
    <p style="font-size: 13px; color: #64748b;">Deadline: End of current business week.</p>
    <p style="font-size: 11px; color: #94a3b8;">People Operations • Employee Wellness Team</p>
</div>""",
                json.dumps([
                    "Third-party generic domain (corp-rewards-portal.info)",
                    "High stakes consequence (loss of benefits coverage)",
                    "Generic greeting lacking personalized employee ID"
                ]),
                "Check your internal HR management system (e.g. Workday, BambooHR) directly rather than clicking links in unexpected benefits emails."
            ),
            (
                "Finance: Urgent Overdue Invoice #INV-2026-981",
                "Finance",
                "High",
                "OVERDUE NOTICE: Outstanding Balance for Cloud Services #INV-2026-981",
                "Accounts Payable",
                "billing-dept@cloud-vendor-invoicing.net",
                """<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 24px; border: 1px solid #e2e8f0; border-radius: 8px;">
    <div style="border-bottom: 2px solid #f59e0b; padding-bottom: 12px; margin-bottom: 20px;">
        <span style="font-size: 18px; font-weight: 700; color: #1e293b;">Global Cloud Infrastructure Services</span>
    </div>
    <h3 style="color: #b45309;">Final Demand: Remittance Due</h3>
    <p>Attention: {{name}},</p>
    <p>Invoice #INV-2026-981 in the amount of <strong>$14,850.00 USD</strong> remains unpaid after multiple prior attempts. Immediate payment settlement is required to prevent suspension of cloud storage clusters.</p>
    <table style="width: 100%; border-collapse: collapse; margin: 20px 0; font-size: 14px;">
        <tr style="background: #f8fafc; border-bottom: 1px solid #cbd5e1;"><td style="padding: 8px;">Invoice:</td><td style="padding: 8px; font-weight: 600;">#INV-2026-981</td></tr>
        <tr style="border-bottom: 1px solid #cbd5e1;"><td style="padding: 8px;">Amount Due:</td><td style="padding: 8px; font-weight: 600; color: #dc2626;">$14,850.00</td></tr>
        <tr style="background: #f8fafc;"><td style="padding: 8px;">Status:</td><td style="padding: 8px; font-weight: 600; color: #b45309;">Delinquent / Critical</td></tr>
    </table>
    <div style="text-align: center; margin: 25px 0;">
        <a href="{{tracking_url}}" style="background-color: #dc2626; color: #ffffff; padding: 12px 24px; border-radius: 6px; text-decoration: none; font-weight: 600; display: inline-block;">Download Invoice & Remittance Details</a>
    </div>
    <p style="font-size: 11px; color: #94a3b8;">Accounts Receivable Billing Division</p>
</div>""",
                json.dumps([
                    "Pressure via high financial claims and threat of service suspension",
                    "External billing portal with no matching vendor record",
                    "Sender email doesn't match official cloud vendor domain",
                    "Direct link prompt instead of attached signed PDF"
                ]),
                "Verify unexpected invoices out-of-band with your internal procurement or finance department before opening external links or paying."
            ),
            (
                "Executive Office: Confidential Board Summary Shared",
                "Operational",
                "High",
                "Confidential: Q3 Strategic Executive Notes Shared with You",
                "Office of the CEO",
                "executive-briefing@cloudshare-secure.org",
                """<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 24px; border: 1px solid #e2e8f0; border-radius: 8px;">
    <div style="border-bottom: 2px solid #6366f1; padding-bottom: 12px; margin-bottom: 20px;">
        <span style="font-size: 18px; font-weight: 700; color: #1e293b;">Enterprise Document Portal</span>
    </div>
    <h3>Secure Document Shared With You</h3>
    <p>Dear {{name}},</p>
    <p>The Executive Leadership team has shared a restricted document with your account:</p>
    <div style="background-color: #f1f5f9; padding: 16px; border-radius: 6px; margin: 16px 0;">
        <p style="margin: 0; font-weight: 600; color: #0f172a;">📄 2026_Q3_Strategic_Realignment_StrictlyConfidential.pdf</p>
        <p style="margin: 4px 0 0; font-size: 12px; color: #64748b;">Size: 3.4 MB • Sensitivity: Confidential Board Level</p>
    </div>
    <p>Please review and acknowledge receipt prior to the executive committee review.</p>
    <div style="text-align: center; margin: 25px 0;">
        <a href="{{tracking_url}}" style="background-color: #4f46e5; color: #ffffff; padding: 12px 24px; border-radius: 6px; text-decoration: none; font-weight: 600; display: inline-block;">Open in Secure Viewer</a>
    </div>
    <p style="font-size: 11px; color: #94a3b8;">Encrypted Storage Service • Access expires in 48 hours</p>
</div>""",
                json.dumps([
                    "Authority impersonation (CEO / Executive office)",
                    "Curiosity-inducing confidential document title",
                    "Third-party sharing domain rather than internal SharePoint or Drive"
                ]),
                "High-level confidential executive files are rarely shared unsolicited without prior heads-up on official communication channels like Slack or Teams."
            ),
            (
                "Logistics: Express Parcel Delivery Delayed",
                "Operational",
                "Low",
                "Notice: Package #FX-982143 held due to incomplete address",
                "Global Parcel Delivery",
                "tracking-update@express-courier-post.com",
                """<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 24px; border: 1px solid #e2e8f0; border-radius: 8px;">
    <div style="border-bottom: 2px solid #059669; padding-bottom: 12px; margin-bottom: 20px;">
        <span style="font-size: 18px; font-weight: 700; color: #1e293b;">Express Courier Delivery</span>
    </div>
    <h3>Delivery Exception Notice</h3>
    <p>Hi {{name}},</p>
    <p>Your scheduled priority shipment #FX-982143 could not be delivered to the corporate reception desk because suite numbers were missing on the shipping manifest.</p>
    <p>Please update your delivery address within 24 hours to schedule re-delivery and avoid the parcel being returned to sender.</p>
    <div style="text-align: center; margin: 25px 0;">
        <a href="{{tracking_url}}" style="background-color: #059669; color: #ffffff; padding: 12px 24px; border-radius: 6px; text-decoration: none; font-weight: 600; display: inline-block;">Confirm Delivery Address</a>
    </div>
    <p style="font-size: 11px; color: #94a3b8;">Automated Postal Operations Center</p>
</div>""",
                json.dumps([
                    "Vague delivery details without sender identity",
                    "Lookalike courier domain",
                    "Common consumer tactic applied to enterprise inboxes"
                ]),
                "Never enter personal or corporate credentials on courier websites linked from unexpected emails. Cross-reference with your actual procurement orders."
            ),
            (
                "Security Operations: Urgent MFA Duo Security Upgrade",
                "IT & Security",
                "Medium",
                "CRITICAL: Immediate Multi-Factor Authentication Migration Required",
                "Enterprise Security Operations Center",
                "soc-alerts@mfa-authenticator-sync.net",
                """<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 24px; border: 1px solid #e2e8f0; border-radius: 8px;">
    <div style="border-bottom: 2px solid #0284c7; padding-bottom: 12px; margin-bottom: 20px;">
        <span style="font-size: 18px; font-weight: 700; color: #1e293b;">Cybersecurity Operations (SecOps)</span>
    </div>
    <h3 style="color: #0369a1;">Mandatory MFA Token Resynchronization</h3>
    <p>Team Member {{name}},</p>
    <p>Due to recent system security audits, legacy hardware and mobile MFA tokens are being migrated to our zero-trust access gateway.</p>
    <p>You must authenticate your active token session to avoid lockout from SSO services.</p>
    <div style="text-align: center; margin: 25px 0;">
        <a href="{{tracking_url}}" style="background-color: #0284c7; color: #ffffff; padding: 12px 24px; border-radius: 6px; text-decoration: none; font-weight: 600; display: inline-block;">Resynchronize MFA Token Now</a>
    </div>
    <p style="font-size: 12px; color: #64748b;">Notice ID: SEC-MFA-9912 • Zero Trust Access Initiative</p>
</div>""",
                json.dumps([
                    "Exploitation of security jargon (MFA, Zero Trust, SecOps) to build false authority",
                    "Suspicious domain (mfa-authenticator-sync.net)",
                    "Attempt to intercept MFA authentication flows"
                ]),
                "Authentic MFA rollouts are coordinated through official internal channels and security town halls, never via unannounced urgent email links."
            )
        ]
        cursor.executemany("""
            INSERT INTO email_templates (name, category, difficulty, subject, sender_name, sender_email, body_html, red_flags, educational_tip)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, templates)

    # 4. Authorized Test Participants
    cursor.execute("SELECT COUNT(*) FROM participants")
    if cursor.fetchone()[0] == 0:
        participants = [
            ("sarah.jenkins@company.internal", "Sarah", "Jenkins", "Finance", 35, 1),
            ("marcus.vance@company.internal", "Marcus", "Vance", "Engineering", 15, 1),
            ("elena.rostova@company.internal", "Elena", "Rostova", "Human Resources", 40, 1),
            ("david.kim@company.internal", "David", "Kim", "Engineering", 20, 1),
            ("chloe.bennett@company.internal", "Chloe", "Bennett", "Sales", 65, 1),
            ("alex.morgan@company.internal", "Alex", "Morgan", "Executive", 25, 1),
            ("rachel.green@company.internal", "Rachel", "Green", "Marketing", 55, 1),
            ("jordan.lee@company.internal", "Jordan", "Lee", "Operations", 45, 1),
            ("liam.smith@company.internal", "Liam", "Smith", "Engineering", 10, 1),
            ("sophia.patel@company.internal", "Sophia", "Patel", "Legal", 30, 1),
            ("lucas.taylor@company.internal", "Lucas", "Taylor", "Sales", 70, 1),
            ("emma.watson@company.internal", "Emma", "Watson", "Finance", 28, 1)
        ]
        cursor.executemany("""
            INSERT INTO participants (email, first_name, last_name, department, risk_score, is_authorized)
            VALUES (?, ?, ?, ?, ?, ?)
        """, participants)

    # 5. Pre-seeded Baseline Campaigns (For immediate realistic analytics & live testing)
    cursor.execute("SELECT COUNT(*) FROM campaigns")
    if cursor.fetchone()[0] == 0:
        now = datetime.now()
        
        # Campaign 1: Completed Baseline Drill (30 days ago)
        c1_time = now - timedelta(days=28)
        cursor.execute("""
            INSERT INTO campaigns (name, template_id, status, delivery_mode, department_target, started_at, completed_at, created_at)
            VALUES (?, 1, 'Completed', 'simulation', 'All', ?, ?, ?)
        """, ("Q3 Baseline Organization Security Drill", fmt_dt(c1_time), fmt_dt(c1_time + timedelta(days=5)), fmt_dt(c1_time - timedelta(days=1))))
        c1_id = cursor.lastrowid

        # Campaign 2: Completed Finance Targeted Drill (14 days ago)
        c2_time = now - timedelta(days=14)
        cursor.execute("""
            INSERT INTO campaigns (name, template_id, status, delivery_mode, department_target, started_at, completed_at, created_at)
            VALUES (?, 3, 'Completed', 'simulation', 'Finance', ?, ?, ?)
        """, ("Finance Dept: Urgent Wire Transfer Drill", fmt_dt(c2_time), fmt_dt(c2_time + timedelta(days=3)), fmt_dt(c2_time - timedelta(days=1))))
        c2_id = cursor.lastrowid

        # Campaign 3: Active Live Drill (Running today - perfect for immediate interactive demo!)
        c3_time = now - timedelta(hours=6)
        cursor.execute("""
            INSERT INTO campaigns (name, template_id, status, delivery_mode, department_target, started_at, completed_at, created_at)
            VALUES (?, 2, 'Active', 'simulation', 'All', ?, NULL, ?)
        """, ("Company-Wide Annual Benefits Simulation", fmt_dt(c3_time), fmt_dt(c3_time)))
        c3_id = cursor.lastrowid

        # Fetch participants
        cursor.execute("SELECT id, email, first_name, department FROM participants")
        all_participants = cursor.fetchall()

        # Seed targets and realistic telemetry events for Campaign 1
        # Realistic metrics: 12 sent, 12 delivered, 11 opened, 4 clicked, 5 reported, 3 trained
        c1_stats = [
            (0, 'Completed Training', 12, 18, None, 25), # Sarah (Finance): Clicked & Trained
            (1, 'Reported', 15, None, 22, None),       # Marcus (Eng): Reported
            (2, 'Completed Training', 30, 45, None, 60), # Elena (HR): Clicked & Trained
            (3, 'Reported', 40, None, 48, None),       # David (Eng): Reported
            (4, 'Clicked', 20, 24, None, None),        # Chloe (Sales): Clicked
            (5, 'Reported', 50, None, 55, None),       # Alex (Exec): Reported
            (6, 'Completed Training', 35, 42, None, 58), # Rachel (Mktg): Clicked & Trained
            (7, 'Opened', 60, None, None, None),       # Jordan (Ops): Opened only
            (8, 'Reported', 25, None, 28, None),       # Liam (Eng): Reported
            (9, 'Reported', 18, None, 21, None),       # Sophia (Legal): Reported
            (10, 'Clicked', 10, 14, None, None),       # Lucas (Sales): Clicked
            (11, 'Opened', 45, None, None, None)        # Emma (Finance): Opened only
        ]

        for p_idx, status, open_m, click_m, rep_m, train_m in c1_stats:
            p = all_participants[p_idx]
            token = str(uuid.uuid4())
            t_sent = c1_time + timedelta(minutes=5)
            t_open = c1_time + timedelta(minutes=open_m) if open_m else None
            t_click = c1_time + timedelta(minutes=click_m) if click_m else None
            t_rep = c1_time + timedelta(minutes=rep_m) if rep_m else None
            t_train = c1_time + timedelta(minutes=train_m) if train_m else None
            score = 100 if t_train else None

            cursor.execute("""
                INSERT INTO campaign_targets (campaign_id, participant_id, tracking_token, status, sent_at, opened_at, clicked_at, reported_at, trained_at, quiz_score, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (c1_id, p['id'], token, status, fmt_dt(t_sent), fmt_dt(t_open), fmt_dt(t_click), fmt_dt(t_rep), fmt_dt(t_train), score, fmt_dt(c1_time)))
            t_id = cursor.lastrowid

            # Add interaction events
            cursor.execute("INSERT INTO interaction_events (campaign_id, participant_id, target_id, event_type, ip_address, created_at) VALUES (?, ?, ?, 'simulated_delivery', '10.0.1.10', ?)", (c1_id, p['id'], t_id, fmt_dt(t_sent)))
            if t_open:
                cursor.execute("INSERT INTO interaction_events (campaign_id, participant_id, target_id, event_type, ip_address, created_at) VALUES (?, ?, ?, 'email_preview', '10.0.1.45', ?)", (c1_id, p['id'], t_id, fmt_dt(t_open)))
            if t_click:
                cursor.execute("INSERT INTO interaction_events (campaign_id, participant_id, target_id, event_type, ip_address, details, created_at) VALUES (?, ?, ?, 'link_clicked', '10.0.1.45', '{\"path\": \"/training/teachable-moment\"}', ?)", (c1_id, p['id'], t_id, fmt_dt(t_click)))
            if t_rep:
                cursor.execute("INSERT INTO interaction_events (campaign_id, participant_id, target_id, event_type, ip_address, created_at) VALUES (?, ?, ?, 'phish_reported', '10.0.1.20', ?)", (c1_id, p['id'], t_id, fmt_dt(t_rep)))
            if t_train:
                cursor.execute("INSERT INTO interaction_events (campaign_id, participant_id, target_id, event_type, ip_address, details, created_at) VALUES (?, ?, ?, 'quiz_completed', '10.0.1.45', '{\"score\": 100, \"answers_correct\": 3}', ?)", (c1_id, p['id'], t_id, fmt_dt(t_train)))

        # Seed targets for Campaign 3 (Active live drill)
        for p in all_participants[:8]:
            token = str(uuid.uuid4())
            sent_time = c3_time + timedelta(minutes=10)
            cursor.execute("""
                INSERT INTO campaign_targets (campaign_id, participant_id, tracking_token, status, sent_at, created_at)
                VALUES (?, ?, ?, 'Sent', ?, ?)
            """, (c3_id, p['id'], token, fmt_dt(sent_time), fmt_dt(c3_time)))
            target_id = cursor.lastrowid
            cursor.execute("INSERT INTO interaction_events (campaign_id, participant_id, target_id, event_type, ip_address, created_at) VALUES (?, ?, ?, 'simulated_delivery', '10.0.2.1', ?)", (c3_id, p['id'], target_id, fmt_dt(sent_time)))

    conn.commit()

