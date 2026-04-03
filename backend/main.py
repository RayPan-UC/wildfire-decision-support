import config  # loads .env variables
from flask import Flask, render_template
from flask_cors import CORS
from api.auth import auth_bp
import sys
import os
from pathlib import Path



# paths
BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR.parent / "frontend"

app = Flask(
    __name__,
    template_folder=str(FRONTEND_DIR)
)
CORS(app)


@app.route("/")
def index():
    return render_template("index.html")

# Register blueprints
app.register_blueprint(auth_bp)

# from api.hotspots   import hotspots_bp
# from api.risk_zones import risk_zones_bp
# from api.chat       import chat_bp
# app.register_blueprint(hotspots_bp)
# app.register_blueprint(risk_zones_bp)
# app.register_blueprint(chat_bp)

if __name__ == '__main__':
    app.run(debug=True, port=5000)