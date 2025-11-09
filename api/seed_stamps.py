# api/seed_stamps.py
from index import app, db
from index import Stamp, UserStamp, User

# Lista de estampillas a insertar
stamps_data = [
    {"name": "Racha corta", "image": "racha_facil.png", "description": "Resuelve todos los Pips 5 días seguidos"},
    {"name": "Racha media", "image": "racha_media.png", "description": "Resuelve todos los Pips 10 días seguidos"},
    {"name": "Racha larga", "image": "racha_dificil.png", "description": "Resuelve todos los Pips 30 días seguidos"},
    {"name": "Racha extrema", "image": "racha_extrema.png", "description": "Resuelve todos los Pips 50 días seguidos"}
]

with app.app_context():
   
    for s in stamps_data:
        if not Stamp.query.filter_by(name=s["name"]).first():
            db.session.add(Stamp(**s))

    db.session.commit()
    print("✅ Estampillas insertadas correctamente!")

   
    users = User.query.all()
    all_stamps = Stamp.query.all()

    # for u in users:
    #     if u.username != "ilopez15":
    #         continue
    #     for i, stamp in enumerate(all_stamps):
    #         if i % 2 == 0:  
    #             if not UserStamp.query.filter_by(user_id=u.id, stamp_id=stamp.id).first():
    #                 db.session.add(UserStamp(user_id=u.id, stamp_id=stamp.id))

    db.session.commit()
    print("✅ UserStamps asignadas para testeo.")
