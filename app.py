import os
from flask import Flask, render_template, session
from dotenv import load_dotenv

from config import Config
from database import init_db, close_db
from routes.public import public_bp
from routes.auth import auth_bp
from routes.dashboard import dashboard_bp
from routes.simulation import simulation_bp
from routes.api import api_bp
from services.security import generate_csrf_token, validate_csrf

load_dotenv()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Database teardown and initialization
    app.teardown_appcontext(close_db)
    with app.app_context():
        init_db(app)

    # Register blueprints
    app.register_blueprint(public_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(simulation_bp)
    app.register_blueprint(api_bp)

    # CSRF Protection Hook
    @app.before_request
    def csrf_protect():
        validate_csrf()

    # Template Context Processors
    @app.context_processor
    def inject_globals():
        return {
            'app_name': app.config.get('APP_NAME', 'PhishGuard'),
            'app_version': app.config.get('APP_VERSION', '2.4.0'),
            'csrf_token': generate_csrf_token,
            'current_user': session.get('username'),
            'user_role': session.get('role')
        }

    # Error Handlers
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('errors/500.html'), 500

    @app.errorhandler(400)
    def bad_request(e):
        return render_template('errors/400.html', description=getattr(e, 'description', 'Bad Request')), 400

    return app

if __name__ == '__main__':
    app = create_app()
    print("=" * 65)
    print("  🛡️  PhishGuard Ethical Phishing Simulation Platform")
    print("  Enterprise Security Awareness & Behavioral Resilience Lab")
    print("  Landing Page: http://127.0.0.1:5000")
    print("  Admin Portal: http://127.0.0.1:5000/login")
    print("  Default Credentials: admin / PhishGuard2026!")
    print("=" * 65)
    app.run(host='0.0.0.0', port=5000, debug=True)
