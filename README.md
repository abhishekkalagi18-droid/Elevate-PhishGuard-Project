# PhishGuard — Ethical Phishing Simulation & Security Awareness Platform

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.x-lightgrey.svg)](https://flask.palletsprojects.com/)
[![SQLite](https://img.shields.io/badge/Database-SQLite3-green.svg)](https://www.sqlite.org/)
[![Chart.js](https://img.shields.io/badge/Visualizations-Chart.js%204.x-orange.svg)](https://www.chartjs.org/)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

**PhishGuard** is a minimalist, enterprise-grade ethical phishing simulation and security-awareness training platform. The application is implemented with Python, Flask, SQLite, HTML, CSS, and JavaScript, with Chart.js for data visualizations. It provides a controlled environment for conducting authorized phishing-awareness exercises and reviewing participant learning outcomes. Engineered for Chief Information Security Officers (CISOs), SecOps professionals, and IT administrators, PhishGuard builds measurable, long-term human resilience through constructive, psychological-safety-focused simulations and instantaneous teachable moments.

---

## 🌟 Key Features

### 1. Enterprise SaaS Design System & Dual Theme Engine
- **Restrained SaaS Aesthetic**: Clean neutral surfaces, subtle borders, restrained shadows, and crisp typography. Avoids neon gradients, clutter, and gratuitous 3D elements.
- **Full Light & Dark Theme Support**: Powered by CSS custom properties with automatic contrast adjustment across surfaces, modals, tables, forms, and charts.
- **Zero-Flash Theme Loading**: Instant theme detection via inline script reading `localStorage` with fallback to system `prefers-color-scheme`.
- **Theme-Aware Chart.js**: Visualizations automatically update their axis colors, grid lines, and tooltip styles when switching between light and dark themes.

### 2. Smooth Scrolling & Viewport Entrance Animations
- **Progressive Section Reveals**: Powered by the modern `IntersectionObserver` API for smooth, upward entrance animations as content scrolls into the viewport.
- **Dynamic Counter Animations**: Animated numeric counters for KPIs with fluid cubic easing (`requestAnimationFrame`).
- **Scroll Progress Indicator**: Unobtrusive reading progress bar fixed to the top edge of the window.
- **Accessibility**: Automatically disables animations when `prefers-reduced-motion` is active.

### 3. Ethical Safeguards & Zero-Credential Policy
- **Zero Password Harvesting**: Simulated links strictly redirect to an educational teachable moment. PhishGuard never requests, intercepts, or logs real credentials, multi-factor codes, session cookies, or secrets.
- **Strict Domain Allowlist**: Dispatches are hard-bounded to pre-authorized domains (`@company.internal`, `@example.com`, `@phishguard.test`). Simulations to unauthorized domains are rejected at the engine level.
- **Non-Punitive Education**: Replaces fear and compliance shaming with supportive micro-learning and positive resilience scoring.

### 4. Interactive Simulation Modes
- **Autonomous Simulation Mode**: Runs 100% out-of-the-box without requiring an external SMTP server. Includes an in-browser simulated corporate webmail client (`/simulate/preview/<token>`).
- **Local SMTP Integration**: Seamlessly connect to a local Mailpit instance (`localhost:1025`) or restricted Postfix server for physical email inbox inspection.
- **Interactive Action Triggers**: Instant one-click triggers in the Campaign Telemetry view allow testers to simulate "Email Opened", "Link Clicked", "Phish Reported", and "Quiz Passed" to verify live telemetry without sending actual emails.

### 5. Immediate Teachable Moments & Micro-Quizzes
- When a simulated link is clicked, the employee is greeted with a calming notification confirming the drill was safe.
- Detailed breakdown of exact red flag indicators present in the scenario (spoofed domains, artificial urgency, deceptive URLs).
- 3-Question interactive awareness quiz that recalculates risk scores and awards a verifiable **Human Resilience Certificate**.

### 6. Comprehensive Executive Reporting
- Executive awareness summary featuring 6-month resilience curves, departmental vulnerability benchmarks, and drill audit trails.
- Exportable as clean, printable HTML / PDF views or CSV audit logs.

---

## 📂 Architecture & Directory Layout

```
phishguard/
├── app.py                      # Application factory, CSRF filter, error handlers
├── config.py                   # Environment configuration & TestConfig
├── database.py                 # SQLite schema initialization & rich seed dataset
├── requirements.txt            # Python dependencies (Flask, python-dotenv, werkzeug)
├── .env.example                # Configuration template
├── models/                     # Data layer abstractions
├── routes/
│   ├── auth.py                 # Administrator session authentication & password hashing
│   ├── public.py               # Public landing page & ethical charter views
│   ├── dashboard.py            # Overview, Campaigns, Templates, Participants, Analytics, Reports
│   ├── simulation.py           # Click tracking, email preview, teachable moment & quiz evaluation
│   └── api.py                  # REST API for stats, chart data, SMTP test & live triggers
├── services/
│   ├── security.py             # CSRF token generator, allowlist validator, email sanitizer
│   ├── email_service.py        # Template rendering & dispatch engine (Simulation / Local SMTP)
│   └── analytics_service.py    # Resilience index, phish-prone %, and timeline calculations
├── static/
│   ├── css/
│   │   ├── main.css            # Design tokens (Light & Dark), reset, badges, buttons, tables
│   │   ├── landing.css         # Hero, features grid, stepper, analytics preview, animations
│   │   ├── dashboard.css       # Sidebar, KPI metric cards, funnel pipeline, modals
│   │   └── training.css        # Simulated webmail client, teachable moment, quiz & certificate
│   ├── js/
│   │   ├── theme.js            # Theme controller (Light/Dark toggle, localStorage sync)
│   │   ├── animations.js       # IntersectionObserver reveals, numeric counter easing
│   │   ├── charts.js           # Theme-responsive Chart.js line and bar visualizers
│   │   └── dashboard.js        # Modals, live action triggers, SMTP socket reachability tester
│   └── vendor/
│       └── chart.umd.min.js    # Self-contained offline Chart.js bundle
├── templates/
│   ├── base.html               # Master layout with zero-flash theme script & scroll progress
│   ├── landing.html            # Public marketing & demonstration landing page
│   ├── ethical_charter.html    # Core ethical principles & privacy commitments
│   ├── auth/
│   │   └── login.html          # Administrator login portal
│   ├── dashboard/
│   │   ├── layout.html         # Dashboard shell with sidebar & header
│   │   ├── overview.html       # KPI metrics & recent activity feed
│   │   ├── campaigns.html      # Campaign management & new campaign creator
│   │   ├── campaign_detail.html# Real-time telemetry funnel & target action triggers
│   │   ├── templates.html      # Educational template gallery & editor
│   │   ├── participants.html   # Participant enrollment & domain allowlist management
│   │   ├── analytics.html      # Deep-dive 6-month trends & departmental comparisons
│   │   ├── training.html       # Awareness curriculum & micro-learning modules
│   │   ├── reports.html        # Executive compliance report with PDF/print view & CSV export
│   │   └── settings.html       # Security parameters & SMTP socket tester
│   ├── simulation/
│   │   ├── email_view.html     # Simulated webmail client with 'Report Phishing' button
│   │   ├── teachable_moment.html# Non-punitive educational intercept with micro-quiz
│   │   ├── quiz_complete.html  # Human Resilience Certificate
│   │   └── reported_success.html# Defensive reinforcement confirmation screen
│   └── errors/
│       ├── 400.html            # Bad Request error page
│       ├── 404.html            # Not Found error page
│       └── 500.html            # Internal Server Error page
└── tests/
    ├── test_auth.py            # Authentication, session security & protected routes
    ├── test_campaigns.py       # Campaign lifecycle & participant dispatch
    ├── test_simulation.py      # Telemetry tracking, link intercept & quiz grading
    └── test_allowlist.py       # Strict domain allowlist enforcement tests
```

---

## ⚡ Quick Start (Windows PowerShell)

Follow these exact commands in **Windows PowerShell** to install dependencies, run the test suite, and launch the platform:

### 1. Navigate to the project directory
```powershell
cd phishguard
```

### 2. Install Python Dependencies
```powershell
pip install -r requirements.txt
```

### 3. Run the Automated Test Suite
Verify that all 12 unit and integration tests pass:
```powershell
python -m unittest discover tests
```

### 4. Start the PhishGuard Application
```powershell
python app.py
```

### 5. Access the Platform
- **Public Landing Page**: [http://127.0.0.1:5000](http://127.0.0.1:5000)
- **Administrative Portal**: [http://127.0.0.1:5000/login](http://127.0.0.1:5000/login)

---

## 🔑 Default Administrator Credentials

For immediate evaluation in local development mode, the database is pre-seeded with:

| Parameter | Value |
| :--- | :--- |
| **Username** | `admin` |
| **Password** | `PhishGuard2026!` |
| **Role** | `admin` |

These are demo credentials for local evaluation only. Change the default password before using the application beyond a local demonstration. Never publish real passwords, API keys, SMTP credentials, or other secrets in the repository.

---

## 🧪 Interactive Live Simulation Walkthrough

1. **Sign in** to the administrative portal using `admin` / `PhishGuard2026!`.
2. Navigate to **Campaigns** in the sidebar. Click on the pre-seeded active campaign **"Company-Wide Annual Benefits Simulation"**.
3. In the **Assigned Simulation Targets** table:
   - Click **`✉️ View Email`** next to any participant. This opens the in-browser simulated corporate email client.
   - Click **`🛡️ Report Phishing`** in the webmail toolbar to observe defensive reporting and score adjustments.
   - Or click the action button inside the email body (e.g., *"View 2026 Benefits Package & Confirm"*). You will be immediately redirected to the **Teachable Moment** screen.
4. Take the 3-question **Micro-Quiz** and click **Submit Answers** to view the generated **Human Resilience Certificate**.
5. Return to the campaign dashboard to watch the funnel and metrics update live!
6. Use the **One-Click Simulation Action Triggers** (`Open`, `Click`, `Report`, `Pass Quiz`) on any row to test real-time telemetry updates instantaneously.

---

## 🛡️ Optional Local SMTP Testing (Mailpit)

If you wish to test physical delivery with a local mock SMTP server:
1. Download and run [Mailpit](https://github.com/axllent/mailpit) (runs on `localhost:1025` for SMTP and `localhost:8025` for webmail).
2. Set `SMTP_ENABLED=true` in your `.env` file.
3. Test connectivity directly from **Dashboard -> Settings -> Local SMTP Integration -> Test SMTP Reachability**.
4. When launching a new campaign, select **Delivery Engine: Local SMTP Server**.

---

## 🔒 Security & Privacy Commitments

- **RFC 2606 Compliant**: Default synthetic test data uses standard reserved domains (`example.com`, `company.internal`).
- **No Password Interception**: Simulation links never present mock credential capture forms that store plaintext passwords or tokens.
- **Strict Allowlisting**: Outbound simulation emails cannot be dispatched to unauthorized external mailboxes.
- **CSRF & Session Hardening**: State-changing requests are protected via cryptographic CSRF tokens, `SameSite=Lax`, and `HttpOnly` cookie flags.
