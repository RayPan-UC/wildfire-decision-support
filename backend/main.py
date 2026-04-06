import config  # loads .env variables
from flask import Flask, render_template
from flask_cors import CORS
from pathlib import Path
from db.connection import db, get_db_uri

BASE_DIR     = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR.parent / "frontend"


def create_app():
    app = Flask(
        __name__,
        template_folder=str(FRONTEND_DIR),
        static_folder=str(FRONTEND_DIR),
        static_url_path='',
    )
    CORS(app)
    app.config['SQLALCHEMY_DATABASE_URI'] = get_db_uri()
    db.init_app(app)

    # ── Blueprints ────────────────────────────────────────────────────────────
    from api.auth      import auth_bp
    from api.events    import events_bp
    from api.timesteps import timesteps_bp

    app.register_blueprint(auth_bp,      url_prefix='/api/auth')
    app.register_blueprint(events_bp,    url_prefix='/api/events')
    app.register_blueprint(timesteps_bp, url_prefix='/api')

    # ── Frontend routes ───────────────────────────────────────────────────────
    @app.route('/')
    def home():
        return render_template('home.htm')

    @app.route('/explore')
    def explore():
        return render_template('index.htm')

    @app.route('/login')
    def login():
        return render_template('login.htm')

    return app


if __name__ == '__main__':
    import threading
    from pipeline.db import setup_db

    app = create_app()

    # DB setup must finish before Flask starts (creates tables, seeds events)
    setup_db(app)

    # Run the slow env-prep + prediction pipeline in the background
    # so Flask starts immediately and serves the UI while data is being built.
    def _background_pipeline():
        from pipeline.env import prepare_all_events
        from pipeline.check import run_checks, build_playback_events, build_realtime_events
        print("=== Preparing environment (background) ===")
        prepare_all_events(app)
        print("=== Building event data (background) ===")
        with app.app_context():
            build_playback_events()
            build_realtime_events()
        print("=== Environment check (background) ===")
        run_checks(app)
        print("=== Pipeline complete ===")

    t = threading.Thread(target=_background_pipeline, daemon=True, name="pipeline")
    t.start()

    app.run(host='0.0.0.0', debug=False, port=5000)
