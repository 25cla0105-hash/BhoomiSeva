import os
import secrets
from datetime import datetime
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or secrets.token_hex(32)

# Set DATABASE_URL to a managed PostgreSQL database for production.
# SQLite is retained as a local-development fallback.
database_url = os.environ.get("DATABASE_URL", "sqlite:///bhoomiseva.db")
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("COOKIE_SECURE", "1") == "1"
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

db = SQLAlchemy(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class Complaint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.String(32), unique=True, nullable=False)
    username = db.Column(db.String(80), nullable=False)
    issue = db.Column(db.String(120), nullable=False)
    details = db.Column(db.Text, default="")
    status = db.Column(db.String(40), default="Submitted", nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


with app.app_context():
    db.create_all()


def current_user():
    uid = session.get("user_id")
    return db.session.get(User, uid) if uid else None


def user_dict(user):
    return {"username": user.username, "name": user.name, "role": user.role}


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user():
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


@app.route("/")
def home():
    return render_template("index.html", user=current_user())


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").lower().strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            session.clear()
            session["user_id"] = user.id
            return redirect(url_for("dashboard"))
        return render_template("login.html", error="Invalid username or password.")
    return render_template("login.html", error=None)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        username = request.form.get("username", "").lower().strip()
        password = request.form.get("password", "")
        role = request.form.get("role", "farmer")
        if role not in {"farmer", "surveyor"}:
            role = "farmer"
        if len(name) < 2 or len(username) < 3 or len(password) < 8:
            return render_template("register.html", error="Use a valid name, username and password (minimum 8 characters).")
        if User.query.filter_by(username=username).first():
            return render_template("register.html", error="Username already exists.")
        user = User(username=username, name=name, role=role, password_hash=generate_password_hash(password))
        db.session.add(user)
        db.session.commit()
        session.clear()
        session["user_id"] = user.id
        return redirect(url_for("dashboard"))
    return render_template("register.html", error=None)


@app.route("/dashboard")
@login_required
def dashboard():
    user = current_user()
    complaints = Complaint.query.filter_by(username=user.username).order_by(Complaint.created_at.desc()).all()
    return render_template("dashboard.html", user=user_dict(user), complaints=complaints)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


@app.route("/feature/<feature>")
@login_required
def feature(feature):
    user = current_user()
    features = {
        "land": ("My Land", "Your land records will appear here after the authorized land-record source is connected."),
        "map": ("Land Survey Map", "Boundary data will appear here after an authorized survey/GIS source is connected."),
        "weather": ("Weather & Rain", "Connect a weather provider to display live conditions for the selected land location."),
        "soil": ("Soil Information", "Connect an authorized soil-data source to display soil and moisture information."),
        "report": ("Report Survey Problem", "Submit a survey or land-record issue for tracking."),
        "complaints": ("My Complaints & Requests", "Track your submitted complaints and requests."),
        "assigned": ("Assigned Surveys", "Survey assignments will appear here for authenticated surveyors."),
        "verify": ("Verify Land", "Land verification data will appear after an authorized land-record source is connected."),
        "boundary": ("Boundary Survey", "Capture and review boundary survey information after the GIS/survey integration is connected."),
        "evidence": ("Evidence Upload", "Secure evidence upload can be enabled when the production storage service is configured."),
        "reports": ("Survey Reports", "Survey reports will appear here when survey records are connected."),
    }
    title, description = features.get(feature, ("BhoomiSeva", "Service"))
    complaints = Complaint.query.filter_by(username=user.username).order_by(Complaint.created_at.desc()).all()
    return render_template("feature.html", user=user_dict(user), title=title, description=description, feature=feature, complaints=complaints)


@app.route("/api/report", methods=["POST"])
@login_required
def api_report():
    user = current_user()
    data = request.get_json(silent=True) or {}
    issue = (data.get("issue") or "Survey problem").strip()[:120]
    details = (data.get("details") or "").strip()[:5000]
    request_id = "BS-" + datetime.utcnow().strftime("%Y%m%d") + "-" + secrets.token_hex(3).upper()
    complaint = Complaint(request_id=request_id, username=user.username, issue=issue, details=details)
    db.session.add(complaint)
    db.session.commit()
    return jsonify({"ok": True, "message": "Request submitted successfully.", "request_id": request_id})


@app.route("/api/health")
def health():
    return jsonify({"ok": True, "service": "BhoomiSeva"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=False)
