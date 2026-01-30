# app.py
"""
Flask backend for conference priority grid system.
Stores 2D grids per page (industrial, logistics, commercial) using JSONB in PostgreSQL.
Automatically ensures default empty data exists for missing pages.
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import IntegrityError
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# Database configuration
DATABASE_URL = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ECHO"] = False
app.config["JSON_SORT_KEYS"] = False  # preserve order in JSON

db = SQLAlchemy(app)

# ----------------- Model Definition -----------------
class PageData(db.Model):
    __tablename__ = "page_data"

    id = db.Column(db.Integer, primary_key=True)
    page_name = db.Column(db.String(50), unique=True, nullable=False, index=True)
    data = db.Column(JSONB, nullable=False, server_default='[]')  # list of lists

    def __repr__(self):
        return f"<PageData {self.page_name}>"

# Create tables if not exist
with app.app_context():
    db.create_all()

# ----------------- Helper: Default Page Data -----------------
DEFAULT_ROWS = {
    "commercial": 4,
    "industrial": 3,
    "logistics": 6
}

DEFAULT_COLUMNS = 9  # Number of data columns (Finance → Security)

def generate_default_data(page_name):
    rows = DEFAULT_ROWS.get(page_name, 3)
    return [["" for _ in range(DEFAULT_COLUMNS)] for _ in range(rows)]

# ----------------- Routes -----------------
@app.route("/load_data/<string:page_name>", methods=["GET"])
def load_data(page_name):
    """
    GET /load_data/<page_name>
    Returns stored 2D array. If missing, creates default empty data.
    """
    record = PageData.query.filter_by(page_name=page_name).first()

    if record is None:
        # Auto-create default empty data for missing page
        default_data = generate_default_data(page_name)
        record = PageData(page_name=page_name, data=default_data)
        db.session.add(record)
        db.session.commit()
        return jsonify(default_data)

    return jsonify(record.data or generate_default_data(page_name))


@app.route("/save_data", methods=["POST"])
def save_data():
    """
    POST /save_data
    Body: { "page": "industrial", "data": [["...", "..."], [...], ...] }
    Overwrites existing data or creates new record.
    """
    try:
        payload = request.get_json(silent=True)
        if not payload or "page" not in payload or "data" not in payload:
            return jsonify({"status": "error", "message": "Missing 'page' or 'data'"}), 400

        page_name = payload["page"]
        new_data = payload["data"]

        # Validate 2D array
        if not isinstance(new_data, list) or any(not isinstance(row, list) for row in new_data):
            return jsonify({"status": "error", "message": "Data must be a 2D list"}), 400

        # Fetch or create record
        record = PageData.query.filter_by(page_name=page_name).first()
        if record:
            record.data = new_data
        else:
            record = PageData(page_name=page_name, data=new_data)
            db.session.add(record)

        db.session.commit()
        return jsonify({"status": "success"})

    except IntegrityError:
        db.session.rollback()
        return jsonify({"status": "error", "message": "Database integrity error"}), 500
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": f"Server error: {str(e)}"}), 500


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

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
