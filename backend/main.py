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
        return render_template('home.htm')

    @app.route('/login')
    def login():
        return render_template('login.htm')

    return app


if __name__ == '__main__':
    from pipeline import build_env
    app = create_app()
    # Werkzeug debug mode runs two processes: reloader parent (WERKZEUG_RUN_MAIN unset)
    # and server child (WERKZEUG_RUN_MAIN=true). Only run build_env once in the child.
    # use_reloader=False avoids the double-run entirely.
    build_env(app)
    app.run(host='0.0.0.0', debug=True, use_reloader=False, port=5000)
