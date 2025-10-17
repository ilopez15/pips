from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date
import os

app = Flask(__name__, template_folder="../templates", static_folder="../static")
app.secret_key = os.environ.get("SECRET_KEY", "supersecretkey")

# Configuración base de datos PostgreSQL (variable DATABASE_URL)
db_url = os.environ.get("DATABASE_URL")
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://")
app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# Modelos
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Result(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    difficulty = db.Column(db.String(20), nullable=False)
    date = db.Column(db.Date, nullable=False)
    minutes = db.Column(db.Integer, nullable=False)
    seconds = db.Column(db.Integer, nullable=False)

# Rutas
@app.route('/')
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return render_template("login.html")

@app.route('/login', methods=["POST"])
def login():
    username = request.form["username"]
    password = request.form["password"]
    user = User.query.filter_by(username=username).first()
    if user and user.check_password(password):
        session["user_id"] = user.id
        return redirect(url_for("dashboard"))
    return render_template("login.html", error="Usuario o contraseña incorrectos")

@app.route('/register', methods=["POST"])
def register():
    username = request.form["username"]
    password = request.form["password"]
    if User.query.filter_by(username=username).first():
        return render_template("login.html", error="El usuario ya existe")
    user = User(username=username)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return render_template("login.html", success="Usuario creado correctamente")

@app.route('/dashboard')
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("index"))
    return render_template("dashboard.html")

@app.route('/submit')
def submit():
    if "user_id" not in session:
        return redirect(url_for("index"))
    user_id = session["user_id"]
    today = date.today()
    results_today = Result.query.filter_by(user_id=user_id, date=today).all()
    completed = {r.difficulty for r in results_today}
    return render_template("submit.html", completed=completed)

@app.route('/submit', methods=["POST"])
def save_result():
    if "user_id" not in session:
        return redirect(url_for("index"))
    user_id = session["user_id"]
    difficulty = request.form["difficulty"]
    minutes = int(request.form["minutes"])
    seconds = int(request.form["seconds"])
    today = date.today()
    existing = Result.query.filter_by(user_id=user_id, difficulty=difficulty, date=today).first()
    if existing:
        return redirect(url_for("submit"))
    result = Result(user_id=user_id, difficulty=difficulty, date=today, minutes=minutes, seconds=seconds)
    db.session.add(result)
    db.session.commit()
    return redirect(url_for("dashboard"))

@app.route('/stats')
def stats():
    if "user_id" not in session:
        return redirect(url_for("index"))
    results = Result.query.order_by(Result.date.asc()).all()
    return render_template("stats.html", results=results)

@app.route('/logout')
def logout():
    session.pop("user_id", None)
    return redirect(url_for("index"))

# Crear tablas al iniciar
with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True)
