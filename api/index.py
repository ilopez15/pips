from flask import Flask, render_template, request, redirect, url_for, session, g, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
import pytz

last_update_date = None

app = Flask(__name__, template_folder="../templates", static_folder="../static")
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "supersecretkey")

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

def fill_missing_results():
    local_tz = pytz.timezone("Europe/Paris")
    today = datetime.now(local_tz).date()
    yesterday = today - datetime.timedelta(days=1)
    print(yesterday)

    difficulties = ["Easy", "Medium", "Hard"]
    users = User.query.all()

    for diff in difficulties:
        # peor resultado del día anterior (mayor tiempo total)
        worst = (
            Result.query.filter_by(date=yesterday, difficulty=diff)
            .order_by(Result.minutes.desc(), Result.seconds.desc())
            .first()
        )

        if not worst:
            continue  # si nadie jugó esa dificultad

        for u in users:
            has_result = (
                Result.query.filter_by(user_id=u.id, date=yesterday, difficulty=diff).first()
                is not None
            )
            if not has_result:
                new_result = Result(
                    user_id=u.id,
                    difficulty=diff,
                    date=yesterday,
                    minutes=worst.minutes,
                    seconds=worst.seconds,
                )
                db.session.add(new_result)
    db.session.commit()
    

# Rellenar g.user para base.html
@app.before_request
def load_user():
    g.user = None
    if "user_id" in session:
        g.user = User.query.get(session["user_id"])


@app.before_request
def auto_update():
    global last_update_date
    local_tz = pytz.timezone("Europe/Paris")
    today = datetime.now(local_tz).date()

    if last_update_date != today:
        fill_missing_results()
        last_update_date = today

b = True
# Rutas
@app.route('/', methods=["GET","POST"])
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session["user_id"] = user.id
            return redirect(url_for("dashboard"))
        flash("Usuario o contraseña incorrectos", "error")
    return render_template("login.html")

@app.route('/register', methods=["GET","POST"])
def register():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if User.query.filter_by(username=username).first():
            flash("El usuario ya existe", "error")
            return render_template("register.html")
        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash("Usuario creado correctamente", "success")
        return redirect(url_for("index"))
    return render_template("register.html")

@app.route('/dashboard')
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("index"))
    return render_template("dashboard.html")

@app.route('/submit', methods=["GET","POST"])
def submit():
    if "user_id" not in session:
        return redirect(url_for("index"))
    
    user_id = session["user_id"]
    local_tz = pytz.timezone("Europe/Paris")  # o tu zona horaria
    today = datetime.now(local_tz).date()
    
    # Ver qué dificultades ya fueron ingresadas hoy
    submitted_results = Result.query.filter_by(user_id=user_id, date=today).all()
    submitted_today = {d: False for d in ["Easy","Medium","Hard"]}
    for r in submitted_results:
        submitted_today[r.difficulty] = True
    print(f"[DEBUG] today = {today}")
    print(f"[DEBUG] submitted_results = {submitted_results}")
    print(f"[DEBUG] submitted_today = {submitted_today}")

    if request.method == "POST":
        for diff in ["Easy","Medium","Hard"]:
            if not submitted_today[diff]:
                min_field = f"{diff.lower()}_min"
                sec_field = f"{diff.lower()}_sec"
                if request.form.get(min_field) and request.form.get(sec_field):
                    minutes = int(request.form[min_field])
                    seconds = int(request.form[sec_field])
                    result = Result(user_id=user_id, difficulty=diff, date=today,
                                    minutes=minutes, seconds=seconds)
                    db.session.add(result)
        db.session.commit()
        flash("Resultados guardados", "success")
        return redirect(url_for("dashboard"))
    
    return render_template("submit.html", submitted_today=submitted_today)

@app.route('/stats')
def stats():
    if "user_id" not in session:
        return redirect(url_for("index"))

    # Obtener todos los resultados
    results = Result.query.join(User).add_columns(
        User.username, Result.difficulty, Result.date, Result.minutes, Result.seconds
    ).all()

    difficulties = ["Easy", "Medium", "Hard"]
    data_by_diff = {}

    for diff in difficulties:
        # filtrar resultados por dificultad
        diff_results = [r for r in results if r.difficulty == diff]

        # obtener todas las fechas únicas y ordenarlas
        dates = sorted({r.date for r in diff_results})
        labels = [d.strftime("%d/%m") for d in dates]

        # obtener todos los usuarios que tienen resultados
        users = sorted({r.username for r in diff_results})
        datasets = []
                # Calcular promedio histórico (en segundos)
        all_seconds = [
            r.minutes * 60 + r.seconds
            for r in diff_results
        ]
        avg_historical = sum(all_seconds) / len(all_seconds) if all_seconds else None

        if avg_historical is not None:
            avg_data = [avg_historical for _ in dates]
            datasets.append({
                "label": "Promedio histórico",
                "data": avg_data,
                "borderDash": [5, 5],  # línea punteada
                "borderColor": "rgba(255, 255, 255, 0.8)",
                "backgroundColor": "transparent",
                "tension": 0,
                "pointRadius": 0
            })

        for u in users:
            # para cada fecha, poner el tiempo en segundos o None si no hay
            data = []
            for d in dates:
                r = next((res for res in diff_results if res.username == u and res.date == d), None)
                if r:
                    total_seconds = r.minutes*60 + r.seconds
                    data.append(total_seconds)
                else:
                    data.append(None)
            datasets.append({"label": u, "data": data})

        data_by_diff[diff] = {"labels": labels, "datasets": datasets}

    return render_template("stats.html", difficulties=difficulties, data_by_diff=data_by_diff)

@app.route('/personalstats')
def personalstats():
    if "user_id" not in session:
        return redirect(url_for("index"))

    user_id = session["user_id"]
    difficulties = ["Easy", "Medium", "Hard"]
    data_by_diff = {}

    for diff in difficulties:
        diff_results = (Result.query
                        .filter_by(user_id=user_id, difficulty=diff)
                        .order_by(Result.date.asc())
                        .all())

        labels = [r.date.strftime("%d/%m") for r in diff_results]
        values = [r.minutes * 60 + r.seconds for r in diff_results]

        datasets = []
        if values:
            avg = sum(values) / len(values)
            datasets.append({
                "label": "Promedio histórico",
                "data": [avg] * len(values),
                "borderDash": [5, 5],
                "borderColor": "rgba(255, 255, 255, 0.8)",
                "backgroundColor": "transparent",
                "tension": 0,
                "pointRadius": 0
            })
            datasets.append({"label": "Tus tiempos", "data": values})

        data_by_diff[diff] = {"labels": labels, "datasets": datasets}

    # 👇 calcula si hay al menos una etiqueta (dato) en cualquier dificultad
    has_data = any(len(data_by_diff[d]["labels"]) > 0 for d in difficulties)

    return render_template(
        "personalstats.html",
        difficulties=difficulties,
        data_by_diff=data_by_diff,
        has_data=has_data  # 👈 pásalo al template
    )


@app.route('/logout')
def logout():
    session.pop("user_id", None)
    return redirect(url_for("index"))

# Crear tablas al iniciar
with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True)
