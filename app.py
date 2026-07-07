import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from flask import Flask, jsonify
from dotenv import load_dotenv

load_dotenv(override=True)

from database import init_db

init_db()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-change-me-in-production")
app.config["PERMANENT_SESSION_LIFETIME"] = 60 * 60 * 24 * 30  # 30 days

_DEV = os.environ.get("FLASK_ENV", "production") == "development"

from blueprints.auth import bp as auth_bp
from blueprints.generation import bp as generation_bp
from blueprints.papers import bp as papers_bp
from blueprints.classroom import bp as classroom_bp
from blueprints.grading import bp as grading_bp

app.register_blueprint(auth_bp)
app.register_blueprint(generation_bp)
app.register_blueprint(papers_bp)
app.register_blueprint(classroom_bp)
app.register_blueprint(grading_bp)


@app.errorhandler(400)
def bad_request(e):
    return jsonify({"error": str(e)}), 400


@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "Internal server error"}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(debug=_DEV, port=port)
