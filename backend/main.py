import config  # loads .env variables
from flask import Flask
from flask_cors import CORS
from pathlib import Path
from db.connection import db, get_db_uri

BASE_DIR     = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR.parent / "frontend"


def create_app():
    app = Flask(__name__)
    CORS(app)
    app.config['SQLALCHEMY_DATABASE_URI'] = get_db_uri()
    db.init_app(app)

    # ── Blueprints ────────────────────────────────────────────────────────────
    from api.auth      import auth_bp
    from api.events    import events_bp
    from api.timesteps import timesteps_bp
    from api.firms     import firms_bp
    from api.config    import config_bp
    from api.satellite  import satellite_bp

    app.register_blueprint(auth_bp,      url_prefix='/api/auth')
    app.register_blueprint(events_bp,    url_prefix='/api/events')
    app.register_blueprint(timesteps_bp, url_prefix='/api')
    app.register_blueprint(firms_bp,     url_prefix='/api/firms')
    app.register_blueprint(config_bp,    url_prefix='/api/config')
    app.register_blueprint(satellite_bp,  url_prefix='/api/satellite')

    # ── Frontend routes ───────────────────────────────────────────────────────
    from flask import send_from_directory

    @app.route('/demo')
    @app.route('/demo/')
    def demo():
        return send_from_directory(str(FRONTEND_DIR), 'index.html')

    @app.route('/css/<path:filename>')
    def frontend_css(filename):
        return send_from_directory(str(FRONTEND_DIR / 'css'), filename)

    @app.route('/js/<path:filename>')
    def frontend_js(filename):
        return send_from_directory(str(FRONTEND_DIR / 'js'), filename)

    @app.route('/demo/<path:filename>')
    def demo_static(filename):
        return send_from_directory(str(FRONTEND_DIR), filename)

    return app


if __name__ == '__main__':
    from pipeline.db import setup_db
    from pipeline.env import prepare_all_events
    from pipeline.check import run_checks, build_playback_events, build_realtime_events

    app = create_app()

    # ── Pipeline (runs to completion before Flask starts) ─────────────────────
    print("=== Setting up database ===")
    setup_db(app)
    print("=== Database ready ===")

    print("=== Preparing environment ===")
    prepare_all_events(app)

    print("=== Building event data ===")
    with app.app_context():
        build_playback_events()
        build_realtime_events()

    print("=== Environment check ===")
    run_checks(app)

    print("=== Pipeline complete — starting Flask ===")
    app.run(host='0.0.0.0', debug=False, port=5000)
