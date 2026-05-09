"""Flask application factory for the launch-ready backend."""

import os
import warnings

warnings.filterwarnings("ignore", message=".*resource_tracker.*")

from flask import Flask, abort, jsonify, request, send_from_directory
from flask_cors import CORS

from .config import Config
from .extensions import limiter
from .utils.logger import get_logger, setup_logger


def create_app(config_class=Config):
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    if hasattr(app, 'json') and hasattr(app.json, 'ensure_ascii'):
        app.json.ensure_ascii = False

    logger = setup_logger('mirofish')
    is_reloader_process = os.environ.get('WERKZEUG_RUN_MAIN') == 'true'
    debug_mode = app.config.get('DEBUG', False)
    should_log_startup = not debug_mode or is_reloader_process

    if should_log_startup:
        logger.info('=' * 50)
        logger.info('Backend starting')
        logger.info('=' * 50)

    cors_origins = app.config.get('CORS_ORIGINS', [])
    if cors_origins:
        CORS(app, resources={r"/api/*": {"origins": cors_origins}})
        if should_log_startup:
            logger.info('CORS enabled for %s', ', '.join(cors_origins))
    elif should_log_startup:
        logger.info('CORS disabled; frontend is expected to use the same origin')

    # Rate limiting
    limiter.init_app(app)
    if should_log_startup:
        logger.info('Rate limiting enabled (300 req/min default per IP)')

    # Optional API-key authentication (enabled only when APP_API_KEY is set)
    app_api_key = app.config.get('APP_API_KEY', '').strip()
    if app_api_key:
        @app.before_request
        def require_api_key():
            if not request.path.startswith('/api/'):
                return
            if request.path == '/api/health':
                return
            provided = (
                request.headers.get('X-Api-Key', '').strip()
                or request.headers.get('Authorization', '').removeprefix('Bearer ').strip()
            )
            if provided != app_api_key:
                return jsonify({"success": False, "error": "Unauthorized"}), 401

        if should_log_startup:
            logger.info('API key authentication enabled')
    elif should_log_startup:
        logger.info('API key authentication disabled (APP_API_KEY not set)')

    from .services.simulation_runner import SimulationRunner

    SimulationRunner.register_cleanup()
    if should_log_startup:
        logger.info('Registered simulation cleanup handler')

    @app.before_request
    def log_request():
        request_logger = get_logger('mirofish.request')
        request_logger.debug('Request: %s %s', request.method, request.path)
        if app.config.get('DEBUG') and app.config.get('LOG_REQUEST_BODIES'):
            if request.content_type and 'json' in request.content_type:
                request_logger.debug('Request body: %s', request.get_json(silent=True))

    @app.after_request
    def log_response(response):
        request_logger = get_logger('mirofish.request')
        request_logger.debug('Response: %s', response.status_code)
        return response

    from .api import graph_bp, report_bp, sentiment_bp, simulation_bp

    app.register_blueprint(graph_bp, url_prefix='/api/graph')
    app.register_blueprint(simulation_bp, url_prefix='/api/simulation')
    app.register_blueprint(report_bp, url_prefix='/api/report')
    app.register_blueprint(sentiment_bp, url_prefix='/api/sentiment')

    @app.route('/health')
    def health():
        return {'status': 'ok', 'service': 'sentiment-simulator-backend'}

    frontend_dist_dir = os.path.abspath(app.config.get('FRONTEND_DIST_DIR', ''))

    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve_frontend(path: str):
        if path.startswith('api/') or path == 'health':
            abort(404)
        if not app.config.get('SERVE_FRONTEND'):
            abort(404)
        if not os.path.isdir(frontend_dist_dir):
            abort(404)

        requested_path = os.path.join(frontend_dist_dir, path)
        if path and os.path.isfile(requested_path):
            return send_from_directory(frontend_dist_dir, path)
        return send_from_directory(frontend_dist_dir, 'index.html')

    if should_log_startup:
        logger.info('Backend ready')

    return app
