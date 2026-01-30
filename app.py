# app.py
"""
Simple Flask backend for the conference priority grid system.
Stores 3×8 grids per page (industrial, logistics, commercial) using JSONB in PostgreSQL.
"""

from flask import Flask, request, jsonify
import os
from dotenv import load_dotenv

# ── Import SQLAlchemy and model ───────────────────────────────────────────────
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import IntegrityError

# Load environment variables (optional but recommended)
load_dotenv()

app = Flask(__name__)
CORS(app)

# ── Database configuration ───────────────────────────────────────────────────
# Using the credentials you provided
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:samson@localhost:5432/conference")

app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ECHO"] = False          # set True only when debugging SQL
app.config["JSON_SORT_KEYS"] = False           # preserve order in JSON responses

db = SQLAlchemy(app)


# ── Model Definition ─────────────────────────────────────────────────────────
class PageData(db.Model):
    __tablename__ = "page_data"

    id = db.Column(db.Integer, primary_key=True)
    page_name = db.Column(db.String(50), unique=True, nullable=False, index=True)
    data = db.Column(JSONB, nullable=False, server_default='[]')  # list of lists

    def __repr__(self):
        return f"<PageData {self.page_name}>"


# Create tables if they don't exist (safe to call multiple times)
with app.app_context():
    db.create_all()


# ── Routes ───────────────────────────────────────────────────────────────────

@app.route("/load_data/<string:page_name>", methods=["GET"])
def load_data(page_name):
    """
    GET /load_data/industrial
    Returns the stored 2D array (or empty list if not found)
    Frontend expects: [ ["val", "val", ...], [...], [...] ]
    """
    record = db.session.query(PageData).filter_by(page_name=page_name).first()
    if record and record.data:
        return jsonify(record.data)
    return jsonify([])


@app.route("/save_data", methods=["POST"])
def save_data():
    """
    POST /save_data
    Body: { "page": "industrial", "data": [["...", "..."], [...], ...] }
    Overwrites existing data for that page or creates new record.
    """
    try:
        payload = request.get_json(silent=True)
        if not payload or "page" not in payload or "data" not in payload:
            return jsonify({
                "status": "error",
                "message": "Missing 'page' or 'data' in request body"
            }), 400

        page_name = payload["page"]
        new_data = payload["data"]

        # Basic validation
        if not isinstance(new_data, list):
            return jsonify({
                "status": "error",
                "message": "data must be a list (2D array)"
            }), 400

        if len(new_data) > 0 and not all(isinstance(row, list) for row in new_data):
            return jsonify({
                "status": "error",
                "message": "data must be list of lists"
            }), 400

        # Find existing record or create new
        record = db.session.query(PageData).filter_by(page_name=page_name).first()

        if record:
            record.data = new_data
        else:
            record = PageData(page_name=page_name, data=new_data)
            db.session.add(record)

        db.session.commit()

        return jsonify({"status": "success"})

    except IntegrityError:
        db.session.rollback()
        return jsonify({
            "status": "error",
            "message": "Database integrity error (possible duplicate page_name)"
        }), 500
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "status": "error",
            "message": f"Server error: {str(e)}"
        }), 500


@app.route("/")
def home():
    return """
    <h1>Conference Priority Grid Backend</h1>
    <p>Endpoints:</p>
    <ul>
        <li>GET /load_data/&lt;page_name&gt;  (industrial | logistics | commercial)</li>
        <li>POST /save_data  (JSON: {"page": "...", "data": [...]})</li>
    </ul>
    """