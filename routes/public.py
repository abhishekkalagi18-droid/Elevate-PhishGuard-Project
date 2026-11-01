from flask import Blueprint, render_template
from services.analytics_service import AnalyticsService

public_bp = Blueprint('public', __name__)

@public_bp.route('/')
def landing():
    """Main landing page highlighting the ethical phishing simulation platform."""
    metrics = AnalyticsService.get_overview_metrics()
    return render_template('landing.html', metrics=metrics)

@public_bp.route('/ethical-charter')
def ethical_charter():
    """Information on PhishGuard ethical safeguards and zero-credential guarantees."""
    return render_template('ethical_charter.html')
