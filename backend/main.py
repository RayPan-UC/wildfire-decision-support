import config  # loads .env variables
from flask import Flask, render_template
from flask_cors import CORS
from pathlib import Path
from db.connection import db, get_db_uri

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR.parent / "frontend"

def create_app():
    app = Flask(
        __name__,
        template_folder=str(FRONTEND_DIR),
        static_folder=str(FRONTEND_DIR),
        static_url_path=''
    )
    CORS(app)

    app.config['SQLALCHEMY_DATABASE_URI'] = get_db_uri()
    db.init_app(app)

    # Register blueprints (imported here to avoid circular imports)
    from api.auth import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/api/auth')

    from api.events import events_bp
    app.register_blueprint(events_bp, url_prefix='/api/events')

    from api.hotspots   import hotspots_bp
    app.register_blueprint(hotspots_bp, url_prefix='/api/hotspots')
    # from api.risk_zones import risk_zones_bp
    # from api.chat       import chat_bp
    # app.register_blueprint(risk_zones_bp, url_prefix='/api/risk-zones')
    # app.register_blueprint(chat_bp, url_prefix='/api/chat')

    @app.route("/")
    def index():
        return render_template("index.htm")

    @app.route("/login")
    def login():
        return render_template("login.htm")

    with app.app_context():
        db.create_all()

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', debug=True, port=5000)
