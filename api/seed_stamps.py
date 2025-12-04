# api/seed_stamps.py
from index import app, db
from index import Stamp, UserStamp, User

# Lista de estampillas a insertar
stamps_data = [
    #Estampillas de racha
    {"name": "Racha corta", "image": "racha_facil", "description": "Resuelve todos los Pips 5 días seguidos.", "category": "1"},
    {"name": "Racha media", "image": "racha_media", "description": "Resuelve todos los Pips 10 días seguidos.", "category": "2"},
    {"name": "Racha larga", "image": "racha_dificil", "description": "Resuelve todos los Pips 30 días seguidos.", "category": "3"},
    {"name": "Racha extrema", "image": "racha_extrema", "description": "Resuelve todos los Pips 50 días seguidos.", "category": "4"}, 
    # {"name": "", "image": "", "description": "", "category": ""}
    #Estampillas de Tiempo
    {"name": "Manos ágiles", "image": "fuego_facil", "description": "Completa el Pips easy en menos de 15 segundos.", "category": "1"},
    {"name": "Manos rápidas", "image": "fuego_medio", "description": "Completa el Pips medium en menos de 45 segundos.", "category": "2"},
    {"name": "Manos turbo", "image": "fuego_dificil", "description": "Completa el Pips hard en menos de 1 minuto.", "category": "3"},
    {"name": "Speedrun", "image": "fuego_extremo", "description": "Resuelve los Pips en menos de 50 segundos cada uno, en un mismo día.", "category": "4"},
    #Estampillas de Resistencia
    {"name": "Prime", "image": "racha_tiempo_extrema", "description": "Haz el Pips hard en menos de 1 minuto, por 5 días seguidos.", "category": "4"},
    #Estampillas miscelaneas
    {"name": "Precoz", "image": "medianoche_media", "description": "Completa todos los Pips en los primeros 5 minutos del día.", "category": "2"}
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
