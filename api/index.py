from flask import Flask, render_template, request, redirect, url_for, session, g, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
import pytz

from dotenv import load_dotenv

load_dotenv()

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
    current_streak = db.Column(db.Integer, nullable=False, default=0)
    last_played = db.Column(db.Date, nullable=False)

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
    

class Stamp(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    image = db.Column(db.String(255), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    category = db.Column(db.Integer, nullable=False)

class UserStamp(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    stamp_id = db.Column(db.Integer, db.ForeignKey('stamp.id'), nullable=False)

def fill_missing_results():
    local_tz = pytz.timezone("Europe/Paris")
    today = datetime.now(local_tz).date()
    yesterday = today - timedelta(days=1)

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
                u.current_streak = 0
                db.session.add(new_result)
    db.session.commit()
    

@app.before_request
def load_user():
    g.user = None
    g.streak_active = False
    g.streak_color = "var(--panel)"  # fallback

    if "user_id" in session:
        user = User.query.get(session["user_id"])
        g.user = user

        # calcular si jugó HOY (Europe/Paris)
        local_tz = pytz.timezone("Europe/Paris")
        today = datetime.now(local_tz).date()

        # Si last_played está definido y es igual a hoy => activo
        try:
            g.streak_active = (user.last_played == today)
        except Exception:
            # si por alguna razón last_played es None o mal, lo consideramos inactivo
            g.streak_active = False

        # Elegir color según la racha (puedes ajustar colores)
        s = (user.current_streak or 0)
        if not g.streak_active:
            # gris cuando no jugó hoy
            g.streak_color = "#3b3b3b"
        else:
            # Paleta por rangos
            if s >= 50:
                g.streak_color = "#ef4444"  # rojo extremo
            elif s >= 30:
                g.streak_color = "#3b82f6"  # violeta
            elif s >= 10:
                g.streak_color = "#ffcc3e"  # amarillo
            elif s >= 5:
                g.streak_color = "#22c55e"  # verde
            else:
                g.streak_color = "#aaf7ff"  # neutro oscuro para rachas pequeñas



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
    won_stamps = session.pop('won_stamps', [])  # lo quita de la session después de leerlo
    won_stamp_names = session.pop('won_stamp_names', [])  # lo quita de la session después de leerlo
    return render_template("dashboard.html", won_stamps=won_stamps, won_stamp_names=won_stamp_names)


@app.route('/submit', methods=["GET","POST"])
def submit():
    if "user_id" not in session:
        return redirect(url_for("index"))

    user_id = session["user_id"]
    user = User.query.get(user_id)
    local_tz = pytz.timezone("Europe/Paris")
    today = datetime.now(local_tz).date()

    #{nombre: Stamp()}
    stamps_racha = {s.name: s for s in Stamp.query.filter(
    Stamp.name.in_(["Racha corta", "Racha media", "Racha larga", "Racha extrema"])).all()}
    stamps_tiempo = {s.name: s for s in Stamp.query.filter(
    Stamp.name.in_(["Manos ágiles", "Manos rápidas", "Manos turbo", "Speedrun"])).all()}
    stamps_misc = {s.name: s for s in Stamp.query.filter(
    Stamp.name.in_(["Precoz"])).all()}
    

    #Flag con la categoria de la stamp
    session["won_stamps"] = []
    session["won_stamp_names"] = []

    # Ver qué dificultades ya fueron ingresadas hoy
    submitted_results = Result.query.filter_by(user_id=user_id, date=today).all()
    submitted_today = {d: False for d in ["Easy","Medium","Hard"]}
    for r in submitted_results:
        submitted_today[r.difficulty] = True

    
    if request.method == "POST":

        #{Dificultad: nombre}
        stamp_mapping = {
            "Easy": "Manos ágiles",
            "Medium": "Manos rápidas",
            "Hard": "Manos turbo",
            "Extreme": "Speedrun"
        }

        #{Dificultad: segundos}
        limites_stamp_tiempo = {
            "Easy": 15, 
            "Medium": 45,
            "Hard": 60
        }

        #Ganas speedrun si llega a 3
        speedrun_flag = 0

        for diff in ["Easy","Medium","Hard"]:

            if not submitted_today[diff]:
                min_field = f"{diff.lower()}_min"
                sec_field = f"{diff.lower()}_sec"
                if request.form.get(min_field) or request.form.get(sec_field):
                    minutes = 0
                    seconds = 0
                    if request.form.get(min_field): 
                        minutes = int(request.form[min_field])
                        
                    if request.form.get(sec_field): 
                        seconds = int(request.form[sec_field])
                        
                    result = Result(user_id=user_id, difficulty=diff, date=today,
                                    minutes=minutes, seconds=seconds)
                    
                    if minutes == 0 and seconds < 50: 
                        speedrun_flag += 1

                    possible_stamp = stamps_tiempo.get(stamp_mapping[diff])
                    if minutes*60 + seconds < limites_stamp_tiempo[diff] and not UserStamp.query.filter_by(user_id=user.id, stamp_id=possible_stamp.id).first():
                        db.session.add(UserStamp(user_id=user.id, stamp_id=possible_stamp.id))

                        session["won_stamps"].append(possible_stamp.category)
                        session["won_stamp_names"].append(possible_stamp.name)

                    db.session.add(result)
                    submitted_today[diff] = True  # marcar como ingresado
        
        if all(submitted_today.values()):
            # obtener los 3 resultados de hoy
            results_today = Result.query.filter_by(user_id=user.id, date=today).all()

            # contar cuántos son <50 segundos
            under_50 = 0
            for r in results_today:
                if r.minutes == 0 and r.seconds < 50:
                    under_50 += 1

            # si los 3 lo cumplen → speedrun
            if under_50 == 3:
                speedrun_stamp = stamps_tiempo.get("Speedrun")
                if speedrun_stamp and not UserStamp.query.filter_by(user_id=user.id, stamp_id=speedrun_stamp.id).first():
                    db.session.add(UserStamp(user_id=user.id, stamp_id=speedrun_stamp.id))
                    session["won_stamps"].append(speedrun_stamp.category)
                    session["won_stamp_names"].append(speedrun_stamp.name)

            yesterday = today - timedelta(days=1)
            if user.last_played == yesterday:
                user.current_streak += 1
                rachas = {5: "Racha corta", 10: "Racha media", 30: "Racha larga", 50: "Racha extrema"}
                for days, stamp_name in rachas.items():
                    if user.current_streak == days:
                        stamp = stamps_racha.get(stamp_name)
                        if stamp and not UserStamp.query.filter_by(user_id=user.id, stamp_id=stamp.id).first():
                            db.session.add(UserStamp(user_id=user.id, stamp_id=stamp.id))
                            session["won_stamps"].append(stamp.category)
                            session["won_stamp_names"].append(stamp_name)
            else:   
                user.current_streak = 1
            user.last_played = today

            stamp_precoz = stamps_misc.get("Precoz")
            if not UserStamp.query.filter_by(user_id=user.id, stamp_id=stamp_precoz.id).first() and datetime.now().strftime("%H") == "00" and int(datetime.now().strftime("%M")) < 5: 
                db.session.add(UserStamp(user_id=user.id, stamp_id=stamp_precoz.id))
                session["won_stamps"].append(stamp_precoz.category)
                session["won_stamp_names"].append("Precoz")
                

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
            if u == "admin":
                continue
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

@app.route('/estampillas')
def estampillas():
    if "user_id" not in session:
        return redirect(url_for("index"))
    user_id = session["user_id"]

    # todas las estampillas
    stamps = Stamp.query.order_by(Stamp.category, Stamp.id).all()
    for stamp in stamps: 
        print(stamp.image)
    # ids de las estampillas del usuario
    user_stamps = {us.stamp_id for us in UserStamp.query.filter_by(user_id=user_id).all()}

    return render_template("estampillas.html", stamps=stamps, user_stamps=user_stamps)

@app.route('/leaderboard')
def leaderboard():
    if "user_id" not in session: 
        return redirect(url_for("index"))

    # Obtener todos los usuarios excepto admin
    users = User.query.filter(User.username != "admin").all()

    data = []
    for u in users:
        # Racha
        streak = u.current_streak

        # Estampillas
        stamp_count = UserStamp.query.filter_by(user_id=u.id).count()

        # Promedios
        averages = {}
        for diff in ["Easy", "Medium", "Hard"]:
            res = db.session.query(
                db.func.avg(Result.minutes*60 + Result.seconds)
            ).filter_by(user_id=u.id, difficulty=diff).scalar()
            averages[diff] = res if res else None

        data.append({
            "username": u.username,
            "streak": streak,
            "stamps": stamp_count,
            "avg_easy": averages["Easy"],
            "avg_medium": averages["Medium"],
            "avg_hard": averages["Hard"],
        })

    return render_template("leaderboard.html", data=data)

    



@app.route('/logout')
def logout():
    session.pop("user_id", None)
    return redirect(url_for("index"))

# Crear tablas al iniciar
with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True)
