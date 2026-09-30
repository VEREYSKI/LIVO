import re
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import os, sqlite3, time, random, smtplib, ssl
from email.message import EmailMessage

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("LIVO_SECRET_KEY", "dev-change-this-secret-key")

BASE_DIR = os.path.dirname(__file__)
USER_DB = os.path.join(BASE_DIR, "livo_users.db")

def init_user_db():
    con = sqlite3.connect(USER_DB)
    con.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE COLLATE NOCASE,
            password_hash TEXT NOT NULL,
            age INTEGER NOT NULL,
            created_at INTEGER NOT NULL,
            email_verified INTEGER NOT NULL DEFAULT 1
        )
    """)
    columns = {row[1] for row in con.execute("PRAGMA table_info(users)").fetchall()}
    if "email_verified" not in columns:
        con.execute("ALTER TABLE users ADD COLUMN email_verified INTEGER NOT NULL DEFAULT 1")
    con.execute("""
        CREATE TABLE IF NOT EXISTS email_verifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            code_hash TEXT NOT NULL,
            expires_at INTEGER NOT NULL,
            attempts INTEGER NOT NULL DEFAULT 0,
            created_at INTEGER NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)
    con.commit()
    con.close()

def send_verification_email(recipient, code):
    host = os.getenv("LIVO_SMTP_HOST", "smtp.gmail.com")
    port = int(os.getenv("LIVO_SMTP_PORT", "587"))
    username = os.getenv("LIVO_SMTP_USERNAME", "livolifnews@gmail.com")
    password = os.getenv("LIVO_SMTP_PASSWORD", "")
    sender = os.getenv("LIVO_MAIL_FROM", "livolifnews@gmail.com")
    if not password:
        raise RuntimeError("Не настроен LIVO_SMTP_PASSWORD")
    msg = EmailMessage()
    msg["Subject"] = "Код подтверждения LIVO"
    msg["From"] = sender
    msg["To"] = recipient
    msg.set_content(
        f"Здравствуйте!\n\nВаш код подтверждения LIVO: {code}\n\n"
        "Код действует 15 минут. Если вы не регистрировались в LIVO, просто проигнорируйте это письмо.\n\nLIVO"
    )
    context = ssl.create_default_context()
    with smtplib.SMTP(host, port, timeout=20) as smtp:
        smtp.ehlo()
        smtp.starttls(context=context)
        smtp.ehlo()
        smtp.login(username, password)
        smtp.send_message(msg)

def create_verification_code(user_id):
    code = f"{random.SystemRandom().randint(0, 999999):06d}"
    con = sqlite3.connect(USER_DB)
    con.execute("DELETE FROM email_verifications WHERE user_id=?", (user_id,))
    con.execute(
        "INSERT INTO email_verifications(user_id,code_hash,expires_at,attempts,created_at) VALUES(?,?,?,?,?)",
        (user_id, generate_password_hash(code), int(time.time()) + 900, 0, int(time.time()))
    )
    con.commit()
    con.close()
    return code

try:
    import sqlite3, time
    init_user_db()
except Exception:
    pass

@app.context_processor
def inject_auth_user():
    user = None
    if session.get("user_id"):
        try:
            con = sqlite3.connect(USER_DB)
            con.row_factory = sqlite3.Row
            user = con.execute("SELECT id, name, email, age FROM users WHERE id=?", (session["user_id"],)).fetchone()
            con.close()
        except Exception:
            user = None
    return {"current_user": user}

MOVIES = [
    {"title": 'Gladiator', "genre": 'Исторический / Боевик', "year": 2000, "rating": "—"},
    {"title": 'Memento', "genre": 'Триллер / Детектив', "year": 2000, "rating": "—"},
    {"title": 'Cast Away', "genre": 'Драма / Приключения', "year": 2000, "rating": "—"},
    {"title": 'Requiem for a Dream', "genre": 'Драма', "year": 2000, "rating": "—"},
    {"title": 'X-Men', "genre": 'Боевик / Фантастика', "year": 2000, "rating": "—"},
    {"title": 'Snatch', "genre": 'Криминал / Комедия', "year": 2000, "rating": "—"},
    {"title": 'The Lord of the Rings: The Fellowship of the Ring', "genre": 'Фэнтези / Приключения', "year": 2001, "rating": "—"},
    {"title": 'Harry Potter and the Sorcerer’s Stone', "genre": 'Фэнтези / Семейный', "year": 2001, "rating": "—"},
    {"title": 'Shrek', "genre": 'Анимация / Комедия', "year": 2001, "rating": "—"},
    {"title": 'Spirited Away', "genre": 'Аниме / Фэнтези', "year": 2001, "rating": "—"},
    {"title": 'A Beautiful Mind', "genre": 'Драма', "year": 2001, "rating": "—"},
    {"title": 'The Fast and the Furious', "genre": 'Боевик / Гонки', "year": 2001, "rating": "—"},
    {"title": 'The Lord of the Rings: The Two Towers', "genre": 'Фэнтези / Приключения', "year": 2002, "rating": "—"},
    {"title": 'Spider-Man', "genre": 'Боевик / Фантастика', "year": 2002, "rating": "—"},
    {"title": 'Harry Potter and the Chamber of Secrets', "genre": 'Фэнтези / Семейный', "year": 2002, "rating": "—"},
    {"title": 'Catch Me If You Can', "genre": 'Драма / Криминал', "year": 2002, "rating": "—"},
    {"title": 'The Bourne Identity', "genre": 'Боевик / Триллер', "year": 2002, "rating": "—"},
    {"title": 'Ice Age', "genre": 'Анимация / Комедия', "year": 2002, "rating": "—"},
    {"title": 'The Lord of the Rings: The Return of the King', "genre": 'Фэнтези / Приключения', "year": 2003, "rating": "—"},
    {"title": 'Pirates of the Caribbean: The Curse of the Black Pearl', "genre": 'Приключения / Фэнтези', "year": 2003, "rating": "—"},
    {"title": 'Finding Nemo', "genre": 'Анимация / Семейный', "year": 2003, "rating": "—"},
    {"title": 'Kill Bill: Vol. 1', "genre": 'Боевик / Триллер', "year": 2003, "rating": "—"},
    {"title": 'Lost in Translation', "genre": 'Драма / Комедия', "year": 2003, "rating": "—"},
    {"title": 'The Matrix Reloaded', "genre": 'Фантастика / Боевик', "year": 2003, "rating": "—"},
    {"title": 'The Incredibles', "genre": 'Анимация / Приключения', "year": 2004, "rating": "—"},
    {"title": 'Eternal Sunshine of the Spotless Mind', "genre": 'Фантастика / Драма', "year": 2004, "rating": "—"},
    {"title": 'Harry Potter and the Prisoner of Azkaban', "genre": 'Фэнтези / Приключения', "year": 2004, "rating": "—"},
    {"title": 'Spider-Man 2', "genre": 'Боевик / Фантастика', "year": 2004, "rating": "—"},
    {"title": 'The Bourne Supremacy', "genre": 'Боевик / Триллер', "year": 2004, "rating": "—"},
    {"title": 'Mean Girls', "genre": 'Комедия', "year": 2004, "rating": "—"},
    {"title": 'Batman Begins', "genre": 'Боевик / Криминал', "year": 2005, "rating": "—"},
    {"title": 'Star Wars: Episode III – Revenge of the Sith', "genre": 'Фантастика / Боевик', "year": 2005, "rating": "—"},
    {"title": 'Harry Potter and the Goblet of Fire', "genre": 'Фэнтези / Приключения', "year": 2005, "rating": "—"},
    {"title": 'Sin City', "genre": 'Криминал / Триллер', "year": 2005, "rating": "—"},
    {"title": 'King Kong', "genre": 'Приключения / Фэнтези', "year": 2005, "rating": "—"},
    {"title": 'The Chronicles of Narnia: The Lion, the Witch and the Wardrobe', "genre": 'Фэнтези / Семейный', "year": 2005, "rating": "—"},
    {"title": 'The Departed', "genre": 'Криминал / Триллер', "year": 2006, "rating": "—"},
    {"title": 'Casino Royale', "genre": 'Боевик / Шпионский', "year": 2006, "rating": "—"},
    {"title": 'The Prestige', "genre": 'Триллер / Драма', "year": 2006, "rating": "—"},
    {"title": 'Pan’s Labyrinth', "genre": 'Фэнтези / Драма', "year": 2006, "rating": "—"},
    {"title": 'Cars', "genre": 'Анимация / Комедия', "year": 2006, "rating": "—"},
    {"title": 'The Pursuit of Happyness', "genre": 'Драма', "year": 2006, "rating": "—"},
    {"title": 'The Dark Knight', "genre": 'Боевик / Криминал', "year": 2007, "rating": "—"},
    {"title": 'Ratatouille', "genre": 'Анимация / Комедия', "year": 2007, "rating": "—"},
    {"title": 'There Will Be Blood', "genre": 'Драма', "year": 2007, "rating": "—"},
    {"title": 'No Country for Old Men', "genre": 'Криминал / Триллер', "year": 2007, "rating": "—"},
    {"title": 'Transformers', "genre": 'Боевик / Фантастика', "year": 2007, "rating": "—"},
    {"title": 'Harry Potter and the Order of the Phoenix', "genre": 'Фэнтези / Приключения', "year": 2007, "rating": "—"},
    {"title": 'The Dark Knight', "genre": 'Боевик / Криминал', "year": 2008, "rating": "—"},
    {"title": 'Iron Man', "genre": 'Боевик / Фантастика', "year": 2008, "rating": "—"},
    {"title": 'WALL-E', "genre": 'Анимация / Фантастика', "year": 2008, "rating": "—"},
    {"title": 'Slumdog Millionaire', "genre": 'Драма', "year": 2008, "rating": "—"},
    {"title": 'Kung Fu Panda', "genre": 'Анимация / Комедия', "year": 2008, "rating": "—"},
    {"title": 'Gran Torino', "genre": 'Драма / Криминал', "year": 2008, "rating": "—"},
    {"title": 'Avatar', "genre": 'Фантастика / Приключения', "year": 2009, "rating": "—"},
    {"title": 'Inglourious Basterds', "genre": 'Военный / Драма', "year": 2009, "rating": "—"},
    {"title": 'Up', "genre": 'Анимация / Приключения', "year": 2009, "rating": "—"},
    {"title": 'The Hangover', "genre": 'Комедия', "year": 2009, "rating": "—"},
    {"title": 'District 9', "genre": 'Фантастика / Боевик', "year": 2009, "rating": "—"},
    {"title": 'Sherlock Holmes', "genre": 'Боевик / Детектив', "year": 2009, "rating": "—"},
    {"title": 'Inception', "genre": 'Фантастика / Триллер', "year": 2010, "rating": "—"},
    {"title": 'The Social Network', "genre": 'Драма', "year": 2010, "rating": "—"},
    {"title": 'Toy Story 3', "genre": 'Анимация / Приключения', "year": 2010, "rating": "—"},
    {"title": 'Shutter Island', "genre": 'Триллер / Детектив', "year": 2010, "rating": "—"},
    {"title": 'How to Train Your Dragon', "genre": 'Анимация / Фэнтези', "year": 2010, "rating": "—"},
    {"title": 'Black Swan', "genre": 'Драма / Триллер', "year": 2010, "rating": "—"},
    {"title": 'Harry Potter and the Deathly Hallows – Part 2', "genre": 'Фэнтези / Приключения', "year": 2011, "rating": "—"},
    {"title": 'Drive', "genre": 'Криминал / Триллер', "year": 2011, "rating": "—"},
    {"title": 'The Intouchables', "genre": 'Драма / Комедия', "year": 2011, "rating": "—"},
    {"title": 'X-Men: First Class', "genre": 'Боевик / Фантастика', "year": 2011, "rating": "—"},
    {"title": 'Rise of the Planet of the Apes', "genre": 'Фантастика / Боевик', "year": 2011, "rating": "—"},
    {"title": 'Bridesmaids', "genre": 'Комедия', "year": 2011, "rating": "—"},
    {"title": 'The Avengers', "genre": 'Боевик / Фантастика', "year": 2012, "rating": "—"},
    {"title": 'The Dark Knight Rises', "genre": 'Боевик / Криминал', "year": 2012, "rating": "—"},
    {"title": 'Django Unchained', "genre": 'Вестерн / Драма', "year": 2012, "rating": "—"},
    {"title": 'Life of Pi', "genre": 'Приключения / Драма', "year": 2012, "rating": "—"},
    {"title": 'Skyfall', "genre": 'Боевик / Шпионский', "year": 2012, "rating": "—"},
    {"title": 'The Hunger Games', "genre": 'Фантастика / Приключения', "year": 2012, "rating": "—"},
    {"title": 'The Wolf of Wall Street', "genre": 'Драма / Криминал', "year": 2013, "rating": "—"},
    {"title": 'Gravity', "genre": 'Фантастика / Триллер', "year": 2013, "rating": "—"},
    {"title": 'Prisoners', "genre": 'Триллер / Детектив', "year": 2013, "rating": "—"},
    {"title": 'Frozen', "genre": 'Анимация / Мюзикл', "year": 2013, "rating": "—"},
    {"title": 'Her', "genre": 'Фантастика / Драма', "year": 2013, "rating": "—"},
    {"title": 'Pacific Rim', "genre": 'Боевик / Фантастика', "year": 2013, "rating": "—"},
    {"title": 'Interstellar', "genre": 'Фантастика / Драма', "year": 2014, "rating": "—"},
    {"title": 'Whiplash', "genre": 'Драма / Музыка', "year": 2014, "rating": "—"},
    {"title": 'Gone Girl', "genre": 'Триллер / Детектив', "year": 2014, "rating": "—"},
    {"title": 'Guardians of the Galaxy', "genre": 'Боевик / Фантастика', "year": 2014, "rating": "—"},
    {"title": 'The Grand Budapest Hotel', "genre": 'Комедия / Драма', "year": 2014, "rating": "—"},
    {"title": 'John Wick', "genre": 'Боевик / Триллер', "year": 2014, "rating": "—"},
    {"title": 'Mad Max: Fury Road', "genre": 'Боевик / Фантастика', "year": 2015, "rating": "—"},
    {"title": 'The Revenant', "genre": 'Драма / Приключения', "year": 2015, "rating": "—"},
    {"title": 'Inside Out', "genre": 'Анимация / Семейный', "year": 2015, "rating": "—"},
    {"title": 'The Martian', "genre": 'Фантастика / Приключения', "year": 2015, "rating": "—"},
    {"title": 'Sicario', "genre": 'Триллер / Криминал', "year": 2015, "rating": "—"},
    {"title": 'Star Wars: The Force Awakens', "genre": 'Фантастика / Приключения', "year": 2015, "rating": "—"},
    {"title": 'La La Land', "genre": 'Мюзикл / Драма', "year": 2016, "rating": "—"},
    {"title": 'Arrival', "genre": 'Фантастика / Драма', "year": 2016, "rating": "—"},
    {"title": 'Deadpool', "genre": 'Боевик / Комедия', "year": 2016, "rating": "—"},
    {"title": 'Zootopia', "genre": 'Анимация / Комедия', "year": 2016, "rating": "—"},
    {"title": 'Doctor Strange', "genre": 'Боевик / Фэнтези', "year": 2016, "rating": "—"},
    {"title": 'Moonlight', "genre": 'Драма', "year": 2016, "rating": "—"},
    {"title": 'Get Out', "genre": 'Ужасы / Триллер', "year": 2017, "rating": "—"},
    {"title": 'Dunkirk', "genre": 'Военный / Драма', "year": 2017, "rating": "—"},
    {"title": 'Blade Runner 2049', "genre": 'Фантастика / Триллер', "year": 2017, "rating": "—"},
    {"title": 'Coco', "genre": 'Анимация / Фэнтези', "year": 2017, "rating": "—"},
    {"title": 'Wonder Woman', "genre": 'Боевик / Фэнтези', "year": 2017, "rating": "—"},
    {"title": 'Thor: Ragnarok', "genre": 'Боевик / Комедия', "year": 2017, "rating": "—"},
    {"title": 'Avengers: Infinity War', "genre": 'Боевик / Фантастика', "year": 2018, "rating": "—"},
    {"title": 'Spider-Man: Into the Spider-Verse', "genre": 'Анимация / Боевик', "year": 2018, "rating": "—"},
    {"title": 'A Quiet Place', "genre": 'Ужасы / Триллер', "year": 2018, "rating": "—"},
    {"title": 'Bohemian Rhapsody', "genre": 'Драма / Музыка', "year": 2018, "rating": "—"},
    {"title": 'Black Panther', "genre": 'Боевик / Фантастика', "year": 2018, "rating": "—"},
    {"title": 'Hereditary', "genre": 'Ужасы / Драма', "year": 2018, "rating": "—"},
    {"title": 'Avengers: Endgame', "genre": 'Боевик / Фантастика', "year": 2019, "rating": "—"},
    {"title": 'Joker', "genre": 'Криминал / Драма', "year": 2019, "rating": "—"},
    {"title": 'Parasite', "genre": 'Триллер / Драма', "year": 2019, "rating": "—"},
    {"title": '1917', "genre": 'Военный / Драма', "year": 2019, "rating": "—"},
    {"title": 'Knives Out', "genre": 'Детектив / Комедия', "year": 2019, "rating": "—"},
    {"title": 'Toy Story 4', "genre": 'Анимация / Приключения', "year": 2019, "rating": "—"},
    {"title": 'Tenet', "genre": 'Фантастика / Боевик', "year": 2020, "rating": "—"},
    {"title": 'Soul', "genre": 'Анимация / Фэнтези', "year": 2020, "rating": "—"},
    {"title": 'Another Round', "genre": 'Драма / Комедия', "year": 2020, "rating": "—"},
    {"title": 'The Invisible Man', "genre": 'Ужасы / Триллер', "year": 2020, "rating": "—"},
    {"title": 'Palm Springs', "genre": 'Комедия / Фантастика', "year": 2020, "rating": "—"},
    {"title": 'Sound of Metal', "genre": 'Драма / Музыка', "year": 2020, "rating": "—"},
    {"title": 'Dune', "genre": 'Фантастика / Приключения', "year": 2021, "rating": "—"},
    {"title": 'Spider-Man: No Way Home', "genre": 'Боевик / Фантастика', "year": 2021, "rating": "—"},
    {"title": 'No Time to Die', "genre": 'Боевик / Шпионский', "year": 2021, "rating": "—"},
    {"title": 'Encanto', "genre": 'Анимация / Фэнтези', "year": 2021, "rating": "—"},
    {"title": 'The Mitchells vs. the Machines', "genre": 'Анимация / Комедия', "year": 2021, "rating": "—"},
    {"title": 'The Green Knight', "genre": 'Фэнтези / Драма', "year": 2021, "rating": "—"},
    {"title": 'Top Gun: Maverick', "genre": 'Боевик / Драма', "year": 2022, "rating": "—"},
    {"title": 'The Batman', "genre": 'Боевик / Криминал', "year": 2022, "rating": "—"},
    {"title": 'Everything Everywhere All at Once', "genre": 'Фантастика / Комедия', "year": 2022, "rating": "—"},
    {"title": 'Avatar: The Way of Water', "genre": 'Фантастика / Приключения', "year": 2022, "rating": "—"},
    {"title": 'All Quiet on the Western Front', "genre": 'Военный / Драма', "year": 2022, "rating": "—"},
    {"title": 'The Banshees of Inisherin', "genre": 'Драма / Комедия', "year": 2022, "rating": "—"},
    {"title": 'Oppenheimer', "genre": 'Драма / История', "year": 2023, "rating": "—"},
    {"title": 'Barbie', "genre": 'Комедия / Фэнтези', "year": 2023, "rating": "—"},
    {"title": 'Spider-Man: Across the Spider-Verse', "genre": 'Анимация / Боевик', "year": 2023, "rating": "—"},
    {"title": 'Guardians of the Galaxy Vol. 3', "genre": 'Боевик / Фантастика', "year": 2023, "rating": "—"},
    {"title": 'John Wick: Chapter 4', "genre": 'Боевик / Триллер', "year": 2023, "rating": "—"},
    {"title": 'The Holdovers', "genre": 'Драма / Комедия', "year": 2023, "rating": "—"},
    {"title": 'Dune: Part Two', "genre": 'Фантастика / Приключения', "year": 2024, "rating": "—"},
    {"title": 'Inside Out 2', "genre": 'Анимация / Семейный', "year": 2024, "rating": "—"},
    {"title": 'Deadpool & Wolverine', "genre": 'Боевик / Комедия', "year": 2024, "rating": "—"},
    {"title": 'The Wild Robot', "genre": 'Анимация / Приключения', "year": 2024, "rating": "—"},
    {"title": 'Wicked', "genre": 'Фэнтези / Мюзикл', "year": 2024, "rating": "—"},
    {"title": 'Furiosa: A Mad Max Saga', "genre": 'Боевик / Фантастика', "year": 2024, "rating": "—"},
    {"title": 'Sinners', "genre": 'Ужасы / Драма', "year": 2025, "rating": "—"},
    {"title": 'A Minecraft Movie', "genre": 'Фэнтези / Приключения', "year": 2025, "rating": "—"},
    {"title": 'F1', "genre": 'Боевик / Спорт', "year": 2025, "rating": "—"},
    {"title": 'Superman', "genre": 'Боевик / Фантастика', "year": 2025, "rating": "—"},
    {"title": 'Thunderbolts*', "genre": 'Боевик / Фантастика', "year": 2025, "rating": "—"},
    {"title": 'The Fantastic Four: First Steps', "genre": 'Боевик / Фантастика', "year": 2025, "rating": "—"},
    {"title": 'Spider-Man: Brand New Day', "genre": 'Боевик / Фантастика', "year": 2026, "rating": "—"},
    {"title": 'The Odyssey', "genre": 'Приключения / Фэнтези', "year": 2026, "rating": "—"},
    {"title": 'Toy Story 5', "genre": 'Анимация / Приключения', "year": 2026, "rating": "—"},
    {"title": 'Minions & Monsters', "genre": 'Анимация / Комедия', "year": 2026, "rating": "—"},
    {"title": 'Moana', "genre": 'Фэнтези / Приключения', "year": 2026, "rating": "—"},
    {"title": 'The End of Oak Street', "genre": 'Фантастика / Триллер', "year": 2026, "rating": "—"},
    {"title": 'PAW Patrol: The Dino Movie', "genre": 'Анимация / Приключения', "year": 2026, "rating": "—"},
    {"title": 'Insidious: Out of the Further', "genre": 'Ужасы / Триллер', "year": 2026, "rating": "—"},
    {"title": 'Mutiny', "genre": 'Боевик / Триллер', "year": 2026, "rating": "—"},
    {"title": 'Coyote vs. ACME', "genre": 'Боевик / Комедия', "year": 2026, "rating": "—"},
    {"title": 'Ice Cream Man', "genre": 'Ужасы / Комедия', "year": 2026, "rating": "—"},
    {"title": 'One Night Only', "genre": 'Комедия / Романтика', "year": 2026, "rating": "—"},
    {"title": 'Super Troopers 3', "genre": 'Комедия / Криминал', "year": 2026, "rating": "—"},
    {"title": 'Soulm8te', "genre": 'Ужасы / Фантастика', "year": 2026, "rating": "—"},
    {"title": 'The Whisper Man', "genre": 'Триллер', "year": 2026, "rating": "—"},
]

GAMES = [
    {"title": 'Grand Theft Auto III', "year": 2001, "genre": 'Action / Open World', "platform": 'PC / PS2 / Xbox'},
    {"title": 'Grand Theft Auto: Vice City', "year": 2002, "genre": 'Action / Open World', "platform": 'PC / PS2 / Xbox'},
    {"title": 'Grand Theft Auto: San Andreas', "year": 2004, "genre": 'Action / Open World', "platform": 'PC / PS2 / Xbox'},
    {"title": 'Grand Theft Auto IV', "year": 2008, "genre": 'Action / Open World', "platform": 'PC / PS3 / Xbox 360'},
    {"title": 'Grand Theft Auto V', "year": 2013, "genre": 'Action / Open World', "platform": 'PC / PS / Xbox'},
    {"title": 'Red Dead Redemption', "year": 2010, "genre": 'Action / Open World', "platform": 'PS3 / Xbox 360'},
    {"title": 'Red Dead Redemption 2', "year": 2018, "genre": 'Action / Open World', "platform": 'PC / PS4 / Xbox One'},
    {"title": 'Watch Dogs', "year": 2014, "genre": 'Action / Open World', "platform": 'PC / PS / Xbox'},
    {"title": 'Watch Dogs 2', "year": 2016, "genre": 'Action / Open World', "platform": 'PC / PS4 / Xbox One'},
    {"title": 'Sleeping Dogs', "year": 2012, "genre": 'Action / Open World', "platform": 'PC / PS / Xbox'},
    {"title": 'Saints Row 2', "year": 2008, "genre": 'Action / Open World', "platform": 'PC / PS3 / Xbox 360'},
    {"title": 'Saints Row: The Third', "year": 2011, "genre": 'Action / Open World', "platform": 'PC / PS / Xbox'},
    {"title": 'Mafia', "year": 2002, "genre": 'Action / Open World', "platform": 'PC / PS2 / Xbox'},
    {"title": 'Mafia II', "year": 2010, "genre": 'Action / Open World', "platform": 'PC / PS3 / Xbox 360'},
    {"title": 'Cyberpunk 2077', "year": 2020, "genre": 'RPG / Open World', "platform": 'PC / PS / Xbox'},
    {"title": 'The Witcher', "year": 2007, "genre": 'RPG', "platform": 'PC'},
    {"title": 'The Witcher 2: Assassins of Kings', "year": 2011, "genre": 'RPG', "platform": 'PC / Xbox 360'},
    {"title": 'The Witcher 3: Wild Hunt', "year": 2015, "genre": 'RPG / Open World', "platform": 'PC / PS / Xbox / Switch'},
    {"title": 'The Elder Scrolls IV: Oblivion', "year": 2006, "genre": 'RPG / Open World', "platform": 'PC / Xbox 360'},
    {"title": 'The Elder Scrolls V: Skyrim', "year": 2011, "genre": 'RPG / Open World', "platform": 'PC / PS / Xbox / Switch'},
    {"title": 'Fallout 3', "year": 2008, "genre": 'RPG / Open World', "platform": 'PC / PS3 / Xbox 360'},
    {"title": 'Fallout: New Vegas', "year": 2010, "genre": 'RPG / Open World', "platform": 'PC / PS3 / Xbox 360'},
    {"title": 'Fallout 4', "year": 2015, "genre": 'RPG / Open World', "platform": 'PC / PS / Xbox'},
    {"title": "Baldur's Gate 3", "year": 2023, "genre": 'RPG', "platform": 'PC / PS5 / Xbox'},
    {"title": 'Dragon Age: Origins', "year": 2009, "genre": 'RPG', "platform": 'PC / PS3 / Xbox 360'},
    {"title": 'Mass Effect', "year": 2007, "genre": 'RPG / Sci-Fi', "platform": 'PC / Xbox / PS'},
    {"title": 'Mass Effect 2', "year": 2010, "genre": 'RPG / Sci-Fi', "platform": 'PC / PS3 / Xbox 360'},
    {"title": 'Mass Effect 3', "year": 2012, "genre": 'RPG / Sci-Fi', "platform": 'PC / PS / Xbox'},
    {"title": 'Elden Ring', "year": 2022, "genre": 'Action RPG', "platform": 'PC / PS / Xbox'},
    {"title": 'Dark Souls', "year": 2011, "genre": 'Action RPG', "platform": 'PC / PS / Xbox'},
    {"title": 'Dark Souls II', "year": 2014, "genre": 'Action RPG', "platform": 'PC / PS / Xbox'},
    {"title": 'Dark Souls III', "year": 2016, "genre": 'Action RPG', "platform": 'PC / PS / Xbox'},
    {"title": 'Sekiro: Shadows Die Twice', "year": 2019, "genre": 'Action RPG', "platform": 'PC / PS4 / Xbox One'},
    {"title": 'Bloodborne', "year": 2015, "genre": 'Action RPG', "platform": 'PS4'},
    {"title": "Demon's Souls", "year": 2020, "genre": 'Action RPG', "platform": 'PS5'},
    {"title": 'Diablo III', "year": 2012, "genre": 'Action RPG', "platform": 'PC / PS / Xbox / Switch'},
    {"title": 'Diablo IV', "year": 2023, "genre": 'Action RPG', "platform": 'PC / PS / Xbox'},
    {"title": 'Path of Exile', "year": 2013, "genre": 'Action RPG', "platform": 'PC / Console'},
    {"title": 'Minecraft', "year": 2011, "genre": 'Sandbox / Survival', "platform": 'PC / Console / Mobile'},
    {"title": 'Terraria', "year": 2011, "genre": 'Sandbox / Survival', "platform": 'PC / Console / Mobile'},
    {"title": 'Starbound', "year": 2016, "genre": 'Sandbox / Survival', "platform": 'PC'},
    {"title": 'Subnautica', "year": 2018, "genre": 'Survival', "platform": 'PC / PS / Xbox / Switch'},
    {"title": 'Subnautica: Below Zero', "year": 2021, "genre": 'Survival', "platform": 'PC / PS / Xbox / Switch'},
    {"title": 'Valheim', "year": 2021, "genre": 'Survival', "platform": 'PC / Xbox'},
    {"title": 'The Forest', "year": 2018, "genre": 'Survival / Horror', "platform": 'PC / PS4'},
    {"title": 'Sons of the Forest', "year": 2024, "genre": 'Survival / Horror', "platform": 'PC / PS5'},
    {"title": 'Rust', "year": 2018, "genre": 'Survival / Online', "platform": 'PC / Console'},
    {"title": 'DayZ', "year": 2013, "genre": 'Survival / Online', "platform": 'PC / PS / Xbox'},
    {"title": 'Hades', "year": 2020, "genre": 'Roguelike / Action', "platform": 'PC / Switch / PS / Xbox'},
    {"title": 'Hades II', "year": 2025, "genre": 'Roguelike / Action', "platform": 'PC'},
    {"title": 'Dead Cells', "year": 2018, "genre": 'Roguelike / Action', "platform": 'PC / Console / Mobile'},
    {"title": 'Risk of Rain 2', "year": 2020, "genre": 'Roguelike / Shooter', "platform": 'PC / Console'},
    {"title": 'Slay the Spire', "year": 2019, "genre": 'Roguelike / Strategy', "platform": 'PC / Console / Mobile'},
    {"title": 'The Binding of Isaac: Rebirth', "year": 2014, "genre": 'Roguelike', "platform": 'PC / Console / Mobile'},
    {"title": 'Hollow Knight', "year": 2017, "genre": 'Metroidvania', "platform": 'PC / Console'},
    {"title": 'Ori and the Blind Forest', "year": 2015, "genre": 'Metroidvania', "platform": 'PC / Xbox / Switch'},
    {"title": 'Ori and the Will of the Wisps', "year": 2020, "genre": 'Metroidvania', "platform": 'PC / Xbox / Switch'},
    {"title": 'Cuphead', "year": 2017, "genre": 'Platformer', "platform": 'PC / Console / Switch'},
    {"title": 'Celeste', "year": 2018, "genre": 'Platformer', "platform": 'PC / Console / Switch'},
    {"title": 'Super Meat Boy', "year": 2010, "genre": 'Platformer', "platform": 'PC / Console'},
    {"title": 'Little Nightmares', "year": 2017, "genre": 'Horror / Platformer', "platform": 'PC / Console'},
    {"title": 'Amnesia: The Dark Descent', "year": 2010, "genre": 'Horror', "platform": 'PC / Console'},
    {"title": 'Outlast', "year": 2013, "genre": 'Horror', "platform": 'PC / Console'},
    {"title": 'Outlast 2', "year": 2017, "genre": 'Horror', "platform": 'PC / Console'},
    {"title": 'Resident Evil 4', "year": 2005, "genre": 'Horror / Action', "platform": 'PC / Console'},
    {"title": 'Resident Evil 7', "year": 2017, "genre": 'Horror', "platform": 'PC / PS / Xbox'},
    {"title": 'Resident Evil Village', "year": 2021, "genre": 'Horror / Action', "platform": 'PC / PS / Xbox'},
    {"title": 'Dead Space', "year": 2008, "genre": 'Horror / Sci-Fi', "platform": 'PC / PS3 / Xbox 360'},
    {"title": 'Dead Space', "year": 2023, "genre": 'Horror / Sci-Fi', "platform": 'PC / PS5 / Xbox Series'},
    {"title": 'Alien: Isolation', "year": 2014, "genre": 'Horror / Survival', "platform": 'PC / Console'},
    {"title": 'The Evil Within', "year": 2014, "genre": 'Horror', "platform": 'PC / Console'},
    {"title": 'Half-Life 2', "year": 2004, "genre": 'FPS / Action', "platform": 'PC / Console'},
    {"title": 'DOOM', "year": 2016, "genre": 'FPS / Action', "platform": 'PC / Console'},
    {"title": 'DOOM Eternal', "year": 2020, "genre": 'FPS / Action', "platform": 'PC / Console / Switch'},
    {"title": 'Quake', "year": 2000, "genre": 'FPS', "platform": 'PC / Console'},
    {"title": 'BioShock', "year": 2007, "genre": 'FPS / Action', "platform": 'PC / Console'},
    {"title": 'BioShock 2', "year": 2010, "genre": 'FPS / Action', "platform": 'PC / Console'},
    {"title": 'BioShock Infinite', "year": 2013, "genre": 'FPS / Action', "platform": 'PC / Console'},
    {"title": 'Portal', "year": 2007, "genre": 'Puzzle / FPS', "platform": 'PC / Console'},
    {"title": 'Portal 2', "year": 2011, "genre": 'Puzzle / FPS', "platform": 'PC / Console'},
    {"title": 'Left 4 Dead', "year": 2008, "genre": 'FPS / Co-op', "platform": 'PC / Xbox 360'},
    {"title": 'Left 4 Dead 2', "year": 2009, "genre": 'FPS / Co-op', "platform": 'PC / Xbox 360'},
    {"title": 'Counter-Strike: Source', "year": 2004, "genre": 'FPS / Online', "platform": 'PC'},
    {"title": 'Counter-Strike: Global Offensive', "year": 2012, "genre": 'FPS / Online', "platform": 'PC'},
    {"title": 'Counter-Strike 2', "year": 2023, "genre": 'FPS / Online', "platform": 'PC'},
    {"title": 'Valorant', "year": 2020, "genre": 'FPS / Online', "platform": 'PC'},
    {"title": 'Overwatch', "year": 2016, "genre": 'FPS / Hero Shooter', "platform": 'PC / Console'},
    {"title": 'Overwatch 2', "year": 2022, "genre": 'FPS / Hero Shooter', "platform": 'PC / Console'},
    {"title": 'Apex Legends', "year": 2019, "genre": 'Battle Royale / FPS', "platform": 'PC / Console / Switch'},
    {"title": 'Fortnite', "year": 2017, "genre": 'Battle Royale / Shooter', "platform": 'PC / Console / Mobile'},
    {"title": 'PUBG: Battlegrounds', "year": 2017, "genre": 'Battle Royale / Shooter', "platform": 'PC / Console / Mobile'},
    {"title": 'Call of Duty 4: Modern Warfare', "year": 2007, "genre": 'FPS', "platform": 'PC / PS / Xbox'},
    {"title": 'Call of Duty: Black Ops', "year": 2010, "genre": 'FPS', "platform": 'PC / PS / Xbox'},
    {"title": 'Call of Duty: Black Ops II', "year": 2012, "genre": 'FPS', "platform": 'PC / PS / Xbox'},
    {"title": 'Call of Duty: Warzone', "year": 2020, "genre": 'Battle Royale / FPS', "platform": 'PC / Console'},
    {"title": 'Battlefield 3', "year": 2011, "genre": 'FPS', "platform": 'PC / PS3 / Xbox 360'},
    {"title": 'Battlefield 4', "year": 2013, "genre": 'FPS', "platform": 'PC / PS / Xbox'},
    {"title": 'Battlefield 1', "year": 2016, "genre": 'FPS', "platform": 'PC / PS4 / Xbox One'},
    {"title": 'Battlefield V', "year": 2018, "genre": 'FPS', "platform": 'PC / PS4 / Xbox One'},
    {"title": 'Battlefield 2042', "year": 2021, "genre": 'FPS', "platform": 'PC / PS / Xbox'},
    {"title": 'Rocket League', "year": 2015, "genre": 'Sports / Racing', "platform": 'PC / Console'},
    {"title": 'FIFA 14', "year": 2013, "genre": 'Sports', "platform": 'PC / PS / Xbox'},
    {"title": 'EA Sports FC 24', "year": 2023, "genre": 'Sports', "platform": 'PC / PS / Xbox / Switch'},
    {"title": 'NBA 2K24', "year": 2023, "genre": 'Sports', "platform": 'PC / PS / Xbox / Switch'},
    {"title": "Tony Hawk's Pro Skater 3", "year": 2001, "genre": 'Sports', "platform": 'PS2 / Xbox / GameCube'},
    {"title": "Tony Hawk's Pro Skater 4", "year": 2002, "genre": 'Sports', "platform": 'PS2 / Xbox / GameCube'},
    {"title": 'Need for Speed: Underground', "year": 2003, "genre": 'Racing', "platform": 'PC / PS2 / Xbox'},
    {"title": 'Need for Speed: Most Wanted', "year": 2005, "genre": 'Racing', "platform": 'PC / PS2 / Xbox'},
    {"title": 'Need for Speed: Carbon', "year": 2006, "genre": 'Racing', "platform": 'PC / PS2 / Xbox'},
    {"title": 'Need for Speed: Hot Pursuit', "year": 2010, "genre": 'Racing', "platform": 'PC / PS3 / Xbox 360'},
    {"title": 'Forza Horizon', "year": 2012, "genre": 'Racing / Open World', "platform": 'Xbox 360'},
    {"title": 'Forza Horizon 4', "year": 2018, "genre": 'Racing / Open World', "platform": 'PC / Xbox'},
    {"title": 'Forza Horizon 5', "year": 2021, "genre": 'Racing / Open World', "platform": 'PC / Xbox'},
    {"title": 'Burnout Paradise', "year": 2008, "genre": 'Racing / Open World', "platform": 'PC / Console'},
    {"title": 'Euro Truck Simulator 2', "year": 2012, "genre": 'Simulation', "platform": 'PC'},
    {"title": 'The Sims 2', "year": 2004, "genre": 'Simulation', "platform": 'PC / Console'},
    {"title": 'The Sims 3', "year": 2009, "genre": 'Simulation', "platform": 'PC / Console'},
    {"title": 'The Sims 4', "year": 2014, "genre": 'Simulation', "platform": 'PC / Console'},
    {"title": 'Cities: Skylines', "year": 2015, "genre": 'Simulation / Strategy', "platform": 'PC / Console'},
    {"title": 'Microsoft Flight Simulator', "year": 2020, "genre": 'Simulation', "platform": 'PC / Xbox'},
    {"title": 'Stardew Valley', "year": 2016, "genre": 'Simulation / Farming', "platform": 'PC / Console / Mobile'},
    {"title": 'Civilization V', "year": 2010, "genre": 'Strategy', "platform": 'PC'},
    {"title": 'Civilization VI', "year": 2016, "genre": 'Strategy', "platform": 'PC / Console / Mobile'},
    {"title": 'XCOM: Enemy Unknown', "year": 2012, "genre": 'Strategy', "platform": 'PC / Console / Mobile'},
    {"title": 'XCOM 2', "year": 2016, "genre": 'Strategy', "platform": 'PC / Console'},
    {"title": 'StarCraft II', "year": 2010, "genre": 'Strategy / RTS', "platform": 'PC'},
    {"title": 'Age of Empires II: Definitive Edition', "year": 2019, "genre": 'Strategy / RTS', "platform": 'PC / Xbox'},
    {"title": 'Age of Empires IV', "year": 2021, "genre": 'Strategy / RTS', "platform": 'PC / Xbox'},
    {"title": 'Dota 2', "year": 2013, "genre": 'MOBA', "platform": 'PC'},
    {"title": 'League of Legends', "year": 2009, "genre": 'MOBA', "platform": 'PC'},
    {"title": 'Roblox', "year": 2006, "genre": 'Sandbox / Online', "platform": 'PC / Console / Mobile'},
    {"title": 'Among Us', "year": 2018, "genre": 'Party / Online', "platform": 'PC / Console / Mobile'},
    {"title": 'Fall Guys', "year": 2020, "genre": 'Party / Online', "platform": 'PC / Console'},
    {"title": 'It Takes Two', "year": 2021, "genre": 'Co-op / Adventure', "platform": 'PC / Console'},
    {"title": 'A Way Out', "year": 2018, "genre": 'Co-op / Adventure', "platform": 'PC / Console'},
    {"title": "Uncharted 4: A Thief's End", "year": 2016, "genre": 'Action / Adventure', "platform": 'PS4'},
    {"title": 'The Last of Us', "year": 2013, "genre": 'Action / Adventure', "platform": 'PS3 / PS4'},
    {"title": 'The Last of Us Part II', "year": 2020, "genre": 'Action / Adventure', "platform": 'PS4 / PS5'},
    {"title": 'God of War', "year": 2018, "genre": 'Action / Adventure', "platform": 'PS4 / PC'},
    {"title": 'God of War Ragnarök', "year": 2022, "genre": 'Action / Adventure', "platform": 'PS / PC'},
    {"title": "Marvel's Spider-Man", "year": 2018, "genre": 'Action / Adventure', "platform": 'PS4 / PC'},
    {"title": "Marvel's Spider-Man 2", "year": 2023, "genre": 'Action / Adventure', "platform": 'PS5 / PC'},
    {"title": 'Horizon Zero Dawn', "year": 2017, "genre": 'Action RPG / Open World', "platform": 'PS4 / PC'},
    {"title": 'Horizon Forbidden West', "year": 2022, "genre": 'Action RPG / Open World', "platform": 'PS4 / PS5 / PC'},
    {"title": 'Ghost of Tsushima', "year": 2020, "genre": 'Action / Open World', "platform": 'PS4 / PS5 / PC'},
    {"title": 'Death Stranding', "year": 2019, "genre": 'Adventure', "platform": 'PS / PC'},
    {"title": 'Hogwarts Legacy', "year": 2023, "genre": 'Action RPG / Open World', "platform": 'PC / Console / Switch'},
    {"title": 'Star Wars Jedi: Fallen Order', "year": 2019, "genre": 'Action / Adventure', "platform": 'PC / Console'},
    {"title": 'Star Wars Jedi: Survivor', "year": 2023, "genre": 'Action / Adventure', "platform": 'PC / Console'},
    {"title": "Assassin's Creed II", "year": 2009, "genre": 'Action / Adventure', "platform": 'PC / Console'},
    {"title": "Assassin's Creed IV: Black Flag", "year": 2013, "genre": 'Action / Open World', "platform": 'PC / Console'},
    {"title": "Assassin's Creed Odyssey", "year": 2018, "genre": 'Action RPG / Open World', "platform": 'PC / Console'},
    {"title": "Assassin's Creed Valhalla", "year": 2020, "genre": 'Action RPG / Open World', "platform": 'PC / Console'},
    {"title": 'Bully', "year": 2006, "genre": 'Action / Adventure', "platform": 'PC / Console'},
    {"title": 'Batman: Arkham Asylum', "year": 2009, "genre": 'Action / Adventure', "platform": 'PC / Console'},
    {"title": 'Batman: Arkham City', "year": 2011, "genre": 'Action / Open World', "platform": 'PC / Console'},
    {"title": 'Batman: Arkham Knight', "year": 2015, "genre": 'Action / Open World', "platform": 'PC / Console'},
    {"title": 'Starfield', "year": 2023, "genre": 'RPG / Open World', "platform": 'PC / Xbox'},
    {"title": 'Palworld', "year": 2024, "genre": 'Survival / RPG', "platform": 'PC / Xbox'},
    {"title": 'Helldivers 2', "year": 2024, "genre": 'Shooter / Co-op', "platform": 'PC / PS5'},
    {"title": 'Black Myth: Wukong', "year": 2024, "genre": 'Action RPG', "platform": 'PC / PS5'},
    {"title": "Dragon's Dogma 2", "year": 2024, "genre": 'Action RPG', "platform": 'PC / PS5 / Xbox'},
    {"title": 'Monster Hunter Wilds', "year": 2025, "genre": 'Action RPG / Co-op', "platform": 'PC / PS5 / Xbox'},
    {"title": "Assassin's Creed Shadows", "year": 2025, "genre": 'Action RPG / Open World', "platform": 'PC / PS5 / Xbox'},
    {"title": 'Death Stranding 2: On the Beach', "year": 2025, "genre": 'Adventure', "platform": 'PS5'},
    {"title": 'Clair Obscur: Expedition 33', "year": 2025, "genre": 'RPG', "platform": 'PC / PS5 / Xbox'},
    {"title": 'Split Fiction', "year": 2025, "genre": 'Co-op / Adventure', "platform": 'PC / PS5 / Xbox'},
    {"title": 'The Alters', "year": 2025, "genre": 'Survival / Strategy', "platform": 'PC / PS5 / Xbox'},
    {"title": 'Resident Evil Requiem', "year": 2026, "genre": 'Horror', "platform": 'PC / PS5 / Xbox Series'},
    {"title": 'Pragmata', "year": 2026, "genre": 'Action / Sci-Fi', "platform": 'PC / PS5 / Xbox Series'},
    {"title": '007 First Light', "year": 2026, "genre": 'Action / Adventure', "platform": 'PC / PS5 / Xbox Series'},
    {"title": 'Marvel 1943: Rise of Hydra', "year": 2026, "genre": 'Action / Adventure', "platform": 'PC / Console'},
    {"title": 'Fable', "year": 2026, "genre": 'RPG / Open World', "platform": 'PC / Xbox'},
    {"title": 'The Witcher 4', "year": 2026, "genre": 'RPG / Open World', "platform": 'PC / Console'},
]

ACTIVITIES = [
    "Посмотри фильм, который давно откладывал.",
    "Выйди на прогулку и найди новое место.",
    "Попробуй приготовить новое блюдо.",
    "Сделай короткую тренировку.",
    "Попробуй новый вид спорта.",
    "Позвони другу, с которым давно не общался.",
    "Начни маленький творческий проект.",
    "Устрой день без бесконечного скроллинга.",
]

CHALLENGES = [
    ("30 дней планки", "30 дней", "Пресс", "Начни с 20 секунд и каждый день добавляй по 5 секунд.", "Новичок"),
    ("Пресс за 21 день", "21 день", "Пресс", "Каждый день: скручивания, подъём коленей и планка.", "Средний"),
    ("100 скручиваний в день", "14 дней", "Пресс", "Разбей 100 скручиваний на несколько подходов в течение дня.", "Продвинутый"),
    ("Приседания 30 дней", "30 дней", "Ноги", "Ежедневно делай приседания, постепенно увеличивая количество.", "Новичок"),
    ("Сильные ноги", "14 дней", "Ноги", "Выпады, приседания и подъёмы на носки через день.", "Средний"),
    ("Ягодичный мост", "21 день", "Ноги", "Каждый день по 3 подхода ягодичного моста.", "Новичок"),
    ("Кардио каждый день", "14 дней", "Кардио", "Минимум 20 минут кардио в день: бег, велосипед или эллипсоид.", "Средний"),
    ("Бег 5 км", "30 дней", "Кардио", "Постепенно подготовься к первой пробежке на 5 км.", "Средний"),
    ("Скакалка 10 минут", "14 дней", "Кардио", "Ежедневно прыгай на скакалке по 10 минут с перерывами.", "Новичок"),
    ("30 дней прогулок", "30 дней", "Активность", "Гуляй каждый день не менее 30 минут.", "Новичок"),
    ("10 000 шагов", "14 дней", "Активность", "Проходи 10 000 шагов в день.", "Средний"),
    ("30 дней спорта", "30 дней", "Активность", "Делай любую тренировку минимум 20 минут в день.", "Средний"),
    ("Новый вид спорта", "7 дней", "Активность", "Каждый день пробуй новую активность: плавание, ролики, йога и другое.", "Новичок"),
    ("30 дней чтения", "30 дней", "Привычка", "Читай не меньше 20 страниц в день.", "Новичок"),
    ("Вода каждый день", "21 день", "Привычка", "Пей не менее 2 литров воды в день.", "Новичок"),
    ("Ранний подъём", "14 дней", "Привычка", "Вставай в одно и то же время и не откладывай будильник.", "Средний"),
    ("День без соцсетей", "7 дней", "Привычка", "Ограничь соцсети до 30 минут в день.", "Средний"),
    ("30 дней новых занятий", "30 дней", "Привычка", "Каждый день пробуй что-то новое: рецепт, навык или хобби.", "Новичок"),
    ("Растяжка каждый день", "21 день", "Гибкость", "Уделяй растяжке 10 минут в день.", "Новичок"),
    ("Шпагат за 30 дней", "30 дней", "Гибкость", "Ежедневная растяжка ног и спины для продвижения к шпагату.", "Продвинутый"),
    ("Утренняя зарядка", "21 день", "Гибкость", "10 минут лёгкой разминки сразу после пробуждения.", "Новичок"),
    ("Тренировка 3 раза в неделю", "4 недели", "Фитнес", "Стабильные тренировки в зале или дома три раза в неделю.", "Средний"),
    ("Фулбади-месяц", "30 дней", "Фитнес", "Тренируйся на всё тело три раза в неделю и записывай веса.", "Средний"),
    ("Отжимания 30 дней", "30 дней", "Фитнес", "Ежедневно добавляй по одному отжиманию к прошлому дню.", "Продвинутый"),
]

CHALLENGE_CATEGORIES = ["Пресс", "Ноги", "Кардио", "Активность", "Привычка", "Гибкость", "Фитнес"]

MUSIC = {'Playboi Carti': ['Magnolia', 'wokeuplikethis*', 'Sky', 'Shoota', 'Location', 'R.I.P.', 'Pissy Pamper', '@ MEH', 'Stop Breathing', 'Sky', '2024'], 'THRILL PILL': ['Молодой трилл', 'Гламурный подонок', 'Rest in Pussy', 'Смерть комментатора', 'Деньги', 'Грустная песня', 'Бентли', 'Миллионы', 'Кто Ты Такая?', 'Было летом'], 'unki': ['Букет', 'Твои глаза', 'Влюбилась', 'Не звони', 'Пустота'], 'Слава КПСС': ['Панкхапр', 'Ваня', 'Гнойный', 'Родина', 'Мой мармеладный'], 'MORGENSHTERN': ['Cadillac', 'El Problema', 'Yung Hefner', 'Новый Мерин', 'ПУСТОЙ ВОКЗАЛ', 'ПОВОД', 'Последняя Любовь', 'ICE', 'Пососи', 'Дом (Лондон, Прага, Ницца)'], 'Big Baby Tape': ['Gimme the Loot', 'Million', 'Turbo', '2K16', 'Dragonborn', 'Bandana', 'Balance', '99 Problems', 'Argumenty', 'Fendi'], 'Baby Cute': ['Моя любовь', 'Не звони', 'Кукла', 'Baby Cute', 'Детка'], 'Дора': ['Втюрилась', 'Дорадура', 'Младшая сестра', 'Пора домой', 'Золотая клетка', 'Барби', 'Мой ангел'], 'CODE80': ['Было летом', 'Кассета', 'Танцуй', 'Плохой день', 'Дождь'], 'CODE10': ['Было летом', 'На повторе', 'Ничего не чувствую', 'Город', 'Поздно'], 'scally Milano': ['Молодость', 'Феникс', 'Мало', 'Не забуду', 'Космос'], 'uglystephan': ['Тесно', 'Не любовь', 'Море', 'Забывай', 'Пока'], 'Voskresenskii': ['Не такой', 'Пока молодой', 'Время', 'Небо', 'Один'], 'YANIX': ['Когда-нибудь', 'Самый молодой', 'Хочу', 'Небо', 'Не сейчас'], 'FORTUNA 812': ['Фортуна', 'Ночь', 'Лови момент', 'Не отпускай', 'Полет'], 'Drake': ["God's Plan", 'Hotline Bling', 'One Dance', 'Started From the Bottom', 'Passionfruit', 'In My Feelings', 'Nonstop', 'Laugh Now Cry Later', 'Rich Flex', 'NOKIA'], 'Travis Scott': ['SICKO MODE', 'goosebumps', 'Antidote', 'HIGHEST IN THE ROOM', 'FE!N', 'BUTTERFLY EFFECT', 'STARGAZING', 'MY EYES', 'I KNOW ?', 'MELTDOWN'], 'Juice WRLD': ['Lucid Dreams', 'All Girls Are the Same', 'Robbery', 'Wishing Well', 'Come & Go', 'Legends', 'Lean Wit Me', 'Righteous', 'Already Dead', 'Bandit'], 'Lil Peep': ['Awful Things', 'Benz Truck', 'Save That Shit', 'Star Shopping', 'Beamer Boy', 'White Wine', 'Hellboy', 'The Brightside', 'Gym Class', 'Falling Down'], 'ARLEKIN 40 000': ['Кукла', 'Танцуй', 'Ночь', 'Медленно', 'Без тебя'], 'MADKID': ['RISE', 'FAITH', 'Bring Back', 'Gold Medal', 'Paranoid', 'RISE (English Version)'], 'VILLAIN': ['Villain', 'Никому', 'Пепел', 'Не спи', 'Последний раз'], 'KUDOKUSHI': ['Метель', 'Пепел', 'Пустота', 'Не уходи', 'Никогда'], 'The Weeknd': ['Blinding Lights', 'Starboy', 'The Hills', "Can't Feel My Face", 'Save Your Tears', 'After Hours', 'Die For You', 'Call Out My Name', 'Popular', 'Timeless'], 'Nirvana': ['Smells Like Teen Spirit', 'Come as You Are', 'Lithium', 'Heart-Shaped Box', 'In Bloom', 'About a Girl', 'The Man Who Sold the World', 'All Apologies', 'Something in the Way', 'Where Did You Sleep Last Night']}


import requests
from urllib.parse import quote

JAMENDO_CLIENT_ID = os.getenv("JAMENDO_CLIENT_ID", "").strip()
MUSIC_DB = os.path.join(os.path.dirname(__file__), "livo_music.db")

def init_music_db():
    con = sqlite3.connect(MUSIC_DB)
    con.execute("""
        CREATE TABLE IF NOT EXISTS music_cache (
            cache_key TEXT PRIMARY KEY,
            payload TEXT NOT NULL,
            saved_at INTEGER NOT NULL
        )
    """)
    con.commit()
    con.close()

def jamendo_search(query, limit=20, offset=0):
    if not JAMENDO_CLIENT_ID:
        return {"error": "JAMENDO_CLIENT_ID не задан", "results": []}
    cache_key = f"{query.lower().strip()}|{limit}|{offset}"
    con = sqlite3.connect(MUSIC_DB)
    row = con.execute(
        "SELECT payload FROM music_cache WHERE cache_key=? AND saved_at>?",
        (cache_key, int(time.time()) - 86400)
    ).fetchone()
    con.close()
    if row:
        import json
        return json.loads(row[0])

    url = "https://api.jamendo.com/v3.0/tracks/"
    params = {
        "client_id": JAMENDO_CLIENT_ID,
        "format": "json",
        "search": query,
        "limit": min(int(limit), 200),
        "offset": int(offset),
        "imagesize": 300,
        "include": "musicinfo"
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        return {"error": f"Не удалось получить музыку: {e}", "results": []}

    import json
    con = sqlite3.connect(MUSIC_DB)
    con.execute(
        "INSERT OR REPLACE INTO music_cache(cache_key,payload,saved_at) VALUES(?,?,?)",
        (cache_key, json.dumps(data, ensure_ascii=False), int(time.time()))
    )
    con.commit()
    con.close()
    return data

try:
    init_music_db()
except Exception:
    pass

try:
    init_user_db()
except Exception:
    pass

FITNESS_EXERCISES = [('Жим лёжа со штангой', 'Грудь', 'Штанга + скамья', '3–4', '8–12'), ('Жим гантелей лёжа', 'Грудь', 'Гантели + скамья', '3–4', '8–12'), ('Жим гантелей на наклонной скамье', 'Верх груди', 'Гантели + наклонная скамья', '3', '8–12'), ('Разводка с гантелями', 'Грудь', 'Гантели + скамья', '3', '10–15'), ('Сведение рук в тренажёре', 'Грудь', 'Пек-дек', '3', '10–15'), ('Отжимания', 'Грудь / трицепс', 'Собственный вес', '3', '8–20'), ('Подтягивания', 'Спина / бицепс', 'Турник', '3–4', '5–12'), ('Тяга верхнего блока', 'Спина', 'Блочный тренажёр', '3–4', '8–12'), ('Тяга горизонтального блока', 'Спина', 'Блочный тренажёр', '3–4', '8–12'), ('Тяга штанги в наклоне', 'Спина', 'Штанга', '3–4', '6–12'), ('Тяга гантели одной рукой', 'Спина', 'Гантель + скамья', '3', '8–12'), ('Гиперэкстензия', 'Поясница / ягодицы', 'Гиперэкстензия', '3', '10–15'), ('Жим ногами', 'Ноги', 'Тренажёр для жима ногами', '3–4', '8–15'), ('Приседания со штангой', 'Ноги / ягодицы', 'Штанга + стойка', '3–4', '6–12'), ('Гакк-присед', 'Ноги', 'Гакк-машина', '3', '8–12'), ('Разгибание ног', 'Квадрицепс', 'Тренажёр разгибания ног', '3', '10–15'), ('Сгибание ног лёжа', 'Бицепс бедра', 'Тренажёр сгибания ног', '3', '10–15'), ('Румынская тяга', 'Задняя поверхность бедра', 'Штанга', '3', '8–12'), ('Выпады с гантелями', 'Ноги / ягодицы', 'Гантели', '3', '8–12 на ногу'), ('Ягодичный мост', 'Ягодицы', 'Штанга / тренажёр', '3–4', '8–15'), ('Подъём на носки стоя', 'Икры', 'Тренажёр / гантели', '3–4', '12–20'), ('Жим гантелей сидя', 'Плечи', 'Гантели + скамья', '3', '8–12'), ('Жим штанги над головой', 'Плечи', 'Штанга', '3', '6–10'), ('Разведения гантелей в стороны', 'Средняя дельта', 'Гантели', '3', '10–15'), ('Обратная бабочка', 'Задняя дельта', 'Тренажёр', '3', '10–15'), ('Тяга каната к лицу', 'Плечи / верх спины', 'Кроссовер', '3', '10–15'), ('Подъём штанги на бицепс', 'Бицепс', 'Штанга', '3', '8–12'), ('Сгибание рук с гантелями', 'Бицепс', 'Гантели', '3', '8–12'), ('Молотковые сгибания', 'Бицепс', 'Гантели', '3', '8–12'), ('Разгибание рук на блоке', 'Трицепс', 'Кроссовер', '3', '10–15'), ('Французский жим', 'Трицепс', 'EZ-штанга / гантель', '3', '8–12'), ('Разгибание руки с гантелью из-за головы', 'Трицепс', 'Гантель', '3', '10–15'), ('Скручивания', 'Пресс', 'Скамья / коврик', '3', '12–20'), ('Подъём коленей в упоре', 'Пресс', 'Турник / брусья', '3', '10–15'), ('Подъём ног в висе', 'Пресс', 'Турник', '3', '8–15'), ('Планка', 'Кор', 'Собственный вес', '3', '30–60 сек'), ('Ролик для пресса', 'Кор', 'Аб-роллер', '3', '6–15'), ('Бёрпи', 'Кардио / всё тело', 'Собственный вес', '3', '8–15'), ('Прыжки на тумбу', 'Ноги / кардио', 'Плио-тумба', '3', '6–12'), ('Канаты', 'Кардио / всё тело', 'Battle ropes', '6', '20–30 сек'), ('Гребля', 'Кардио / всё тело', 'Гребной тренажёр', '1', '10–20 мин'), ('Беговая дорожка', 'Кардио', 'Беговая дорожка', '1', '15–30 мин'), ('Велотренажёр', 'Кардио', 'Велотренажёр', '1', '15–30 мин'), ('Эллиптический тренажёр', 'Кардио', 'Эллипсоид', '1', '15–30 мин'), ('Степпер', 'Кардио', 'Степпер', '1', '10–20 мин')]

PC_PARTS = {'cpu': ['AMD Ryzen 5 5600', 'AMD Ryzen 5 7600', 'AMD Ryzen 5 9600X', 'AMD Ryzen 7 7800X3D', 'AMD Ryzen 7 9800X3D', 'Intel Core i5-14400F', 'Intel Core i5-14600K', 'Intel Core i7-14700K', 'Intel Core Ultra 7 265K'], 'gpu': ['NVIDIA GeForce RTX 4060 8GB', 'NVIDIA GeForce RTX 4060 Ti 8GB', 'NVIDIA GeForce RTX 4070 SUPER 12GB', 'NVIDIA GeForce RTX 4070 Ti SUPER 16GB', 'NVIDIA GeForce RTX 5070 12GB', 'NVIDIA GeForce RTX 5070 Ti 16GB', 'NVIDIA GeForce RTX 5080 16GB', 'AMD Radeon RX 7600 8GB', 'AMD Radeon RX 7800 XT 16GB', 'AMD Radeon RX 7900 XTX 24GB'], 'ram': ['16GB DDR4', '32GB DDR4', '16GB DDR5', '32GB DDR5', '64GB DDR5'], 'storage': ['1TB NVMe SSD', '2TB NVMe SSD', '1TB SATA SSD + 2TB NVMe SSD', '2TB NVMe SSD + 4TB HDD'], 'psu': ['550W 80+ Bronze', '650W 80+ Gold', '750W 80+ Gold', '850W 80+ Gold', '1000W 80+ Gold'], 'cooler': ['Boxed/Air cooler', 'Tower air cooler', '240mm AIO', '360mm AIO'], 'motherboard': ['B550', 'B650', 'B850', 'Z790', 'B760', 'Z890'], 'case': ['Mid Tower Airflow', 'Mid Tower RGB', 'Full Tower', 'Compact ATX']}
FPS_PROFILES = {'RTX 4060': {'1080p': {'Fortnite': 173, 'CS2': 317, 'Valorant': 465, 'Cyberpunk 2077': 77, 'GTA V': 149, 'Warzone': 110, 'Red Dead Redemption 2': 78, 'Minecraft': 365}, '1440p': {'Fortnite': 110, 'CS2': 210, 'Valorant': 397, 'Cyberpunk 2077': 58, 'GTA V': 101, 'Warzone': 75, 'Red Dead Redemption 2': 55, 'Minecraft': 231}, '4K': {'Fortnite': 58, 'CS2': 117, 'Valorant': 317, 'Cyberpunk 2077': 38, 'GTA V': 58, 'Warzone': 44, 'Red Dead Redemption 2': 31, 'Minecraft': 121}}, 'RTX 4070 SUPER': {'1080p': {'Fortnite': 265, 'CS2': 487, 'Valorant': 487, 'Cyberpunk 2077': 109, 'GTA V': 229, 'Warzone': 177, 'Red Dead Redemption 2': 126, 'Minecraft': 561}, '1440p': {'Fortnite': 168, 'CS2': 323, 'Valorant': 462, 'Cyberpunk 2077': 89, 'GTA V': 155, 'Warzone': 158, 'Red Dead Redemption 2': 94, 'Minecraft': 354}, '4K': {'Fortnite': 89, 'CS2': 180, 'Valorant': 429, 'Cyberpunk 2077': 59, 'GTA V': 89, 'Warzone': 133, 'Red Dead Redemption 2': 62, 'Minecraft': 185}}, 'RTX 5070': {'1080p': {'Fortnite': 290, 'CS2': 500, 'Valorant': 600, 'Cyberpunk 2077': 125, 'GTA V': 240, 'Warzone': 190, 'Red Dead Redemption 2': 135, 'Minecraft': 600}, '1440p': {'Fortnite': 210, 'CS2': 390, 'Valorant': 540, 'Cyberpunk 2077': 95, 'GTA V': 175, 'Warzone': 160, 'Red Dead Redemption 2': 105, 'Minecraft': 450}, '4K': {'Fortnite': 120, 'CS2': 220, 'Valorant': 390, 'Cyberpunk 2077': 65, 'GTA V': 95, 'Warzone': 105, 'Red Dead Redemption 2': 70, 'Minecraft': 230}}, 'RTX 5070 Ti': {'1080p': {'Fortnite': 320, 'CS2': 550, 'Valorant': 650, 'Cyberpunk 2077': 145, 'GTA V': 260, 'Warzone': 220, 'Red Dead Redemption 2': 155, 'Minecraft': 650}, '1440p': {'Fortnite': 240, 'CS2': 430, 'Valorant': 570, 'Cyberpunk 2077': 115, 'GTA V': 195, 'Warzone': 190, 'Red Dead Redemption 2': 125, 'Minecraft': 500}, '4K': {'Fortnite': 150, 'CS2': 250, 'Valorant': 430, 'Cyberpunk 2077': 80, 'GTA V': 110, 'Warzone': 125, 'Red Dead Redemption 2': 82, 'Minecraft': 270}}}

RECIPES = [('Омлет с сыром', 'Очень просто', 'Завтрак', '10 мин', ['2 яйца', '30 г сыра', '1 ч. л. масла', 'соль'], ['Взбей яйца с солью.', 'Разогрей сковороду с маслом.', 'Влей яйца, посыпь сыром и готовь 3–5 минут.']), ('Горячие бутерброды', 'Очень просто', 'Завтрак', '10 мин', ['4 ломтика хлеба', 'сыр', 'помидор', 'ветчина по желанию'], ['Собери бутерброды.', 'Запекай при 180°C около 7–10 минут.', 'Подавай горячими.']), ('Паста с чесноком', 'Очень просто', 'Обед', '15 мин', ['200 г пасты', '2 зубчика чеснока', '2 ст. л. масла', 'сыр'], ['Отвари пасту.', 'Обжарь чеснок в масле 1–2 минуты.', 'Смешай с пастой и сыром.']), ('Картофель по-деревенски', 'Просто', 'Гарнир', '40 мин', ['500 г картофеля', '1 ст. л. масла', 'паприка', 'соль'], ['Нарежь картофель дольками.', 'Перемешай со специями и маслом.', 'Запекай при 200°C 30–35 минут.']), ('Кесадилья с сыром', 'Просто', 'Перекус', '15 мин', ['2 тортильи', '100 г сыра', 'кукуруза', 'помидор'], ['Разложи начинку на тортилье.', 'Накрой второй и обжарь на сухой сковороде.', 'Нарежь треугольниками.']), ('Домашняя пицца', 'Просто', 'Ужин', '45 мин', ['тесто', 'томатный соус', 'сыр', 'помидоры', 'грибы'], ['Раскатай тесто.', 'Добавь соус и начинку.', 'Выпекай при 220°C 12–15 минут.']), ('Курица терияки', 'Средне', 'Ужин', '30 мин', ['500 г курицы', 'соевый соус', 'мёд', 'чеснок', 'рис'], ['Нарежь курицу и обжарь.', 'Добавь соевый соус, мёд и чеснок.', 'Подавай с рисом.']), ('Рамен дома', 'Средне', 'Ужин', '30 мин', ['лапша', 'бульон', 'яйцо', 'грибы', 'зелёный лук'], ['Приготовь бульон.', 'Добавь лапшу и грибы.', 'Подавай с варёным яйцом и зелёным луком.']), ('Шакшука', 'Средне', 'Завтрак', '25 мин', ['4 яйца', '400 г томатов', 'лук', 'перец', 'паприка'], ['Обжарь лук и перец.', 'Добавь томаты и специи.', 'Сделай углубления, разбей яйца и накрой крышкой.']), ('Тыквенный крем-суп', 'Средне', 'Суп', '40 мин', ['500 г тыквы', 'лук', '500 мл бульона', 'сливки'], ['Запеки или потуши тыкву с луком.', 'Добавь бульон и провари.', 'Измельчи блендером и добавь сливки.']), ('Лазанья', 'Средне', 'Ужин', '90 мин', ['листы лазаньи', 'фарш', 'томатный соус', 'сыр', 'бешамель'], ['Приготовь мясной соус.', 'Выкладывай слоями пасту, соус и сыр.', 'Запекай при 180°C около 40 минут.']), ('Домашние суши-роллы', 'Средне', 'Ужин', '60 мин', ['рис для суши', 'нори', 'огурец', 'авокадо', 'лосось или креветка'], ['Приготовь рис.', 'Разложи рис на нори и добавь начинку.', 'Сверни ролл и нарежь.']), ('Гёдза', 'Необычно', 'Ужин', '60 мин', ['тесто для гёдза', 'фарш', 'капуста', 'имбирь', 'соевый соус'], ['Смешай начинку.', 'Сформируй небольшие пельмени.', 'Обжарь дно, добавь немного воды и накрой крышкой.']), ('Корейский корн-дог', 'Необычно', 'Перекус', '40 мин', ['сосиски', 'моцарелла', 'мука', 'молоко', 'панировочные сухари'], ['Насади сосиску и сыр на шпажку.', 'Окуни в густое тесто и сухари.', 'Обжарь до золотистой корочки.']), ('Домашний поке', 'Необычно', 'Обед', '25 мин', ['рис', 'лосось или тофу', 'авокадо', 'огурец', 'кунжут'], ['Приготовь рис.', 'Нарежь ингредиенты.', 'Собери всё в миске и добавь соус.']), ('Тако с хрустящей курицей', 'Необычно', 'Ужин', '45 мин', ['тортильи', 'курица', 'панировка', 'салат', 'томатный соус'], ['Запанируй и приготовь курицу.', 'Прогрей тортильи.', 'Собери тако с овощами и соусом.']), ('Паста в съедобной сырной корзинке', 'Необычно', 'Ужин', '35 мин', ['паста', 'твёрдый сыр', 'сливочный соус', 'грибы'], ['Растопи сыр на сковороде и сформируй корзинку.', 'Приготовь пасту и соус.', 'Положи пасту в сырную корзинку.']), ('Радужные панкейки', 'Необычно', 'Завтрак', '30 мин', ['мука', 'молоко', 'яйца', 'разрыхлитель', 'пищевые красители'], ['Сделай тесто и раздели на части.', 'Добавь немного пищевого красителя.', 'Испеки маленькие панкейки и сложи стопкой.']), ('Шоколадная лава-кейк', 'Необычно', 'Десерт', '25 мин', ['100 г шоколада', '50 г масла', '2 яйца', '50 г сахара', '30 г муки'], ['Растопи шоколад с маслом.', 'Смешай с яйцами, сахаром и мукой.', 'Запекай при 200°C примерно 8–10 минут.']), ('Мороженое из банана', 'Очень просто', 'Десерт', '10 мин + заморозка', ['2 банана', 'какао или ягоды'], ['Заморозь нарезанные бананы.', 'Пробей блендером до кремовой текстуры.', 'Добавь какао или ягоды.']), ('Тирамису в стакане', 'Средне', 'Десерт', '30 мин', ['печенье савоярди', 'маскарпоне', 'кофе', 'какао'], ['Сделай крем из маскарпоне.', 'Обмакни печенье в кофе.', 'Выложи слоями и охлади.']), ('Японский чизкейк', 'Необычно', 'Десерт', '90 мин', ['сливочный сыр', 'яйца', 'молоко', 'мука', 'сахар'], ['Приготовь нежное тесто.', 'Перелей в форму.', 'Выпекай на водяной бане при умеренной температуре.']), ('Домашняя лапша с арахисовым соусом', 'Необычно', 'Обед', '25 мин', ['лапша', 'арахисовая паста', 'соевый соус', 'лайм', 'чеснок'], ['Отвари лапшу.', 'Смешай ингредиенты соуса.', 'Перемешай лапшу с соусом и добавь кунжут.']), ('Хрустящий нут', 'Просто', 'Перекус', '35 мин', ['консервированный нут', 'масло', 'паприка', 'соль'], ['Промой и хорошо обсуши нут.', 'Смешай со специями и маслом.', 'Запекай при 200°C 25–30 минут.']), ('Яблочный крамбл', 'Просто', 'Десерт', '40 мин', ['яблоки', 'овсяные хлопья', 'мука', 'масло', 'сахар'], ['Нарежь яблоки.', 'Смешай крошку из хлопьев, муки и масла.', 'Запекай при 180°C около 25 минут.']), ('Овсянка с бананом', 'Очень просто', 'Завтрак', '8 мин', ['60 г овсянки', '200 мл молока', '1 банан', 'корица'], ['Свари овсянку на молоке.', 'Добавь банан и корицу.', 'Подавай тёплой.']), ('Яичница с овощами', 'Очень просто', 'Завтрак', '10 мин', ['2 яйца', 'помидор', 'перец', '1 ч. л. масла'], ['Нарежь овощи.', 'Обжарь овощи 2–3 минуты.', 'Добавь яйца и готовь до желаемой степени.']), ('Творожная миска с ягодами', 'Очень просто', 'Завтрак', '5 мин', ['200 г творога', 'ягоды', 'банан', '1 ч. л. мёда'], ['Положи творог в миску.', 'Добавь ягоды и банан.', 'При желании добавь мёд.']), ('Сырники', 'Просто', 'Завтрак', '25 мин', ['250 г творога', '1 яйцо', '2 ст. л. муки', '1 ч. л. сахара'], ['Смешай творог, яйцо, муку и сахар.', 'Сформируй сырники.', 'Обжарь по 3–4 минуты с каждой стороны.']), ('Французские тосты', 'Просто', 'Завтрак', '15 мин', ['4 ломтика хлеба', '1 яйцо', '100 мл молока', 'корица'], ['Взбей яйцо с молоком.', 'Обмакни хлеб.', 'Обжарь с двух сторон до золотистой корочки.']), ('Гречка с грибами', 'Очень просто', 'Обед', '25 мин', ['150 г гречки', '200 г грибов', 'лук', '1 ст. л. масла'], ['Свари гречку.', 'Обжарь лук и грибы.', 'Смешай с гречкой.']), ('Рис с овощами', 'Очень просто', 'Обед', '20 мин', ['200 г риса', 'морковь', 'горошек', 'кукуруза', 'соевый соус'], ['Свари рис.', 'Обжарь овощи.', 'Добавь рис и немного соевого соуса.']), ('Куриный суп с лапшой', 'Просто', 'Суп', '40 мин', ['300 г курицы', '1 л воды', 'морковь', 'лук', 'лапша'], ['Отвари курицу.', 'Добавь овощи.', 'Всыпь лапшу и вари до готовности.']), ('Чечевичный суп', 'Просто', 'Суп', '35 мин', ['200 г чечевицы', 'морковь', 'лук', '1 л бульона', 'паприка'], ['Обжарь лук и морковь.', 'Добавь чечевицу и бульон.', 'Вари до мягкости чечевицы.']), ('Томатный суп', 'Очень просто', 'Суп', '25 мин', ['500 г томатов', 'лук', '500 мл бульона', 'базилик'], ['Обжарь лук.', 'Добавь томаты и бульон.', 'Провари и измельчи блендером.']), ('Салат Цезарь с курицей', 'Просто', 'Обед', '25 мин', ['куриная грудка', 'салат', 'помидоры', 'сухарики', 'сыр'], ['Приготовь курицу.', 'Нарежь салат и овощи.', 'Смешай ингредиенты и добавь соус.']), ('Греческий салат', 'Очень просто', 'Обед', '10 мин', ['огурец', 'помидоры', 'фета', 'маслины', 'лук'], ['Нарежь овощи и сыр.', 'Добавь маслины.', 'Заправь маслом и перемешай.']), ('Тёплый салат с курицей', 'Просто', 'Обед', '25 мин', ['курица', 'салат', 'перец', 'помидоры', 'масло'], ['Обжарь курицу и перец.', 'Добавь овощи.', 'Подавай тёплым с салатными листьями.']), ('Буррито с фасолью', 'Просто', 'Обед', '20 мин', ['2 тортильи', 'фасоль', 'рис', 'кукуруза', 'сыр'], ['Прогрей фасоль и рис.', 'Выложи начинку на тортильи.', 'Сверни буррито и подрумянь на сковороде.']), ('Куриные котлеты', 'Просто', 'Ужин', '30 мин', ['500 г куриного фарша', '1 яйцо', 'лук', '2 ст. л. сухарей'], ['Смешай все ингредиенты.', 'Сформируй котлеты.', 'Обжарь или запеки до полной готовности.']), ('Лосось с овощами', 'Просто', 'Ужин', '30 мин', ['2 филе лосося', 'брокколи', 'морковь', 'лимон'], ['Выложи рыбу и овощи на противень.', 'Добавь лимон.', 'Запекай при 200°C около 20 минут.']), ('Овощи с тофу в соусе', 'Просто', 'Ужин', '25 мин', ['200 г тофу', 'перец', 'брокколи', 'соевый соус', 'кунжут'], ['Нарежь тофу и овощи.', 'Обжарь до румяности.', 'Добавь соевый соус и кунжут.']), ('Спагетти болоньезе', 'Средне', 'Ужин', '40 мин', ['200 г спагетти', '300 г фарша', 'томатный соус', 'лук', 'пармезан'], ['Отвари спагетти.', 'Приготовь мясной соус с луком и томатами.', 'Смешай и посыпь сыром.']), ('Ризотто с грибами', 'Средне', 'Ужин', '40 мин', ['200 г риса арборио', '200 г грибов', 'лук', '700 мл бульона', 'пармезан'], ['Обжарь лук и грибы.', 'Добавляй бульон порциями к рису.', 'В конце добавь пармезан.']), ('Овощная паста', 'Просто', 'Ужин', '25 мин', ['200 г пасты', 'кабачок', 'помидоры', 'чеснок', 'сыр'], ['Отвари пасту.', 'Обжарь овощи с чесноком.', 'Смешай с пастой и сыром.']), ('Картофельное пюре', 'Очень просто', 'Гарнир', '25 мин', ['500 г картофеля', '50 мл молока', '20 г масла', 'соль'], ['Отвари картофель.', 'Разомни с маслом.', 'Добавь тёплое молоко и соль.']), ('Запечённые овощи', 'Очень просто', 'Гарнир', '35 мин', ['кабачок', 'перец', 'морковь', 'лук', 'масло'], ['Нарежь овощи.', 'Перемешай с маслом и специями.', 'Запекай при 200°C 25–30 минут.']), ('Рис с чесноком', 'Очень просто', 'Гарнир', '20 мин', ['200 г риса', '2 зубчика чеснока', '1 ст. л. масла', 'соль'], ['Свари рис.', 'Обжарь чеснок в масле.', 'Смешай с рисом.']), ('Овощные оладьи', 'Просто', 'Перекус', '25 мин', ['кабачок', '1 яйцо', '3 ст. л. муки', 'зелень'], ['Натри кабачок и отожми влагу.', 'Смешай с яйцом и мукой.', 'Обжарь небольшими порциями.']), ('Хумус с овощами', 'Очень просто', 'Перекус', '10 мин', ['нут', 'тахини', 'лимон', 'чеснок', 'морковь', 'огурец'], ['Измельчи нут, тахини, лимон и чеснок.', 'Добавь немного воды до кремовой текстуры.', 'Подавай с нарезанными овощами.']), ('Йогурт с гранолой', 'Очень просто', 'Перекус', '5 мин', ['200 г йогурта', 'гранола', 'ягоды', 'банан'], ['Выложи йогурт в миску.', 'Добавь гранолу.', 'Укрась ягодами и бананом.']), ('Фруктовый смузи', 'Очень просто', 'Перекус', '5 мин', ['банан', 'ягоды', '200 мл молока или йогурта'], ['Положи всё в блендер.', 'Взбей до однородности.', 'Подавай сразу.']), ('Яблочные оладьи', 'Просто', 'Десерт', '20 мин', ['1 яблоко', '1 яйцо', '100 мл молока', '100 г муки'], ['Натри яблоко.', 'Смешай с остальными ингредиентами.', 'Обжарь небольшими оладьями.']), ('Шоколадный мусс', 'Средне', 'Десерт', '20 мин + охлаждение', ['150 г тёмного шоколада', '2 яйца', '1 ст. л. сахара'], ['Растопи шоколад.', 'Отдели белки и взбей их.', 'Аккуратно смешай и охлади.']), ('Запечённые яблоки', 'Очень просто', 'Десерт', '30 мин', ['2 яблока', 'корица', 'орехи', '1 ч. л. мёда'], ['Удалить сердцевину.', 'Наполни яблоки орехами и корицей.', 'Запекай при 180°C около 20 минут.']), ('Чиа-пудинг', 'Очень просто', 'Завтрак', '5 мин + охлаждение', ['3 ст. л. семян чиа', '200 мл молока', 'ягоды', 'банан'], ['Смешай чиа с молоком.', 'Оставь в холодильнике минимум на 2 часа.', 'Добавь фрукты перед подачей.']), ('Кускус с овощами', 'Очень просто', 'Обед', '15 мин', ['200 г кускуса', 'перец', 'огурец', 'помидоры', 'зелень'], ['Залей кускус горячей водой по инструкции.', 'Нарежь овощи.', 'Смешай и добавь зелень.']), ('Тунец с фасолью', 'Очень просто', 'Обед', '10 мин', ['тунец', 'белая фасоль', 'помидоры', 'лук', 'лимон'], ['Слей жидкость с тунца и фасоли.', 'Нарежь овощи.', 'Смешай и заправь лимонным соком.']), ('Курица с картофелем в духовке', 'Просто', 'Ужин', '55 мин', ['500 г курицы', '500 г картофеля', 'морковь', 'масло', 'паприка'], ['Нарежь картофель и овощи.', 'Смешай всё со специями и маслом.', 'Запекай при 200°C до полной готовности.']), ('Овощной вок с лапшой', 'Просто', 'Ужин', '25 мин', ['лапша', 'брокколи', 'перец', 'морковь', 'соевый соус'], ['Приготовь лапшу.', 'Быстро обжарь овощи на сильном огне.', 'Добавь лапшу и соевый соус.']), ('Пита с курицей и овощами', 'Просто', 'Перекус', '20 мин', ['2 питы', 'курица', 'салат', 'огурец', 'томатный соус'], ['Приготовь курицу.', 'Нарежь овощи.', 'Наполни питы курицей и овощами.']), ('Авокадо-тост с яйцом', 'Очень просто', 'Завтрак', '10 мин', ['2 ломтика хлеба', '1 авокадо', '2 яйца', 'лимон', 'соль'], ['Подрумянь хлеб.', 'Разомни авокадо с лимоном и солью.', 'Приготовь яйца и выложи на тосты.']), ('Банановые панкейки', 'Просто', 'Завтрак', '20 мин', ['1 банан', '2 яйца', '60 г овсянки', 'корица'], ['Разомни банан.', 'Смешай все ингредиенты.', 'Обжарь небольшие панкейки с двух сторон.']), ('Овсянка с яблоком', 'Очень просто', 'Завтрак', '10 мин', ['60 г овсянки', '200 мл молока', '1 яблоко', 'корица'], ['Свари овсянку.', 'Нарежь яблоко.', 'Добавь яблоко и корицу перед подачей.']), ('Омлет со шпинатом', 'Очень просто', 'Завтрак', '12 мин', ['3 яйца', 'горсть шпината', '30 г сыра', '1 ч. л. масла'], ['Взбей яйца.', 'Слегка обжарь шпинат.', 'Залей яйцами, добавь сыр и доведи до готовности.']), ('Гранола с йогуртом', 'Очень просто', 'Завтрак', '5 мин', ['200 г йогурта', '50 г гранолы', 'ягоды', 'банан'], ['Выложи йогурт.', 'Добавь гранолу.', 'Укрась ягодами и бананом.']), ('Булгур с курицей', 'Просто', 'Обед', '30 мин', ['200 г булгура', '300 г курицы', 'перец', 'морковь', 'лук'], ['Обжарь курицу.', 'Добавь овощи.', 'Всыпь булгур и готовь до мягкости.']), ('Гречка с курицей', 'Очень просто', 'Обед', '30 мин', ['200 г гречки', '300 г курицы', 'лук', 'морковь'], ['Свари гречку.', 'Обжарь курицу с овощами.', 'Смешай и прогрей вместе.']), ('Паста с курицей и сливками', 'Средне', 'Обед', '30 мин', ['200 г пасты', '300 г курицы', '150 мл сливок', 'чеснок', 'пармезан'], ['Отвари пасту.', 'Обжарь курицу с чесноком.', 'Добавь сливки, пасту и сыр.']), ('Кускус с курицей', 'Просто', 'Обед', '25 мин', ['200 г кускуса', '250 г курицы', 'огурец', 'помидор', 'зелень'], ['Приготовь кускус.', 'Приготовь курицу.', 'Смешай с овощами и зеленью.']), ('Суп-пюре из брокколи', 'Просто', 'Суп', '30 мин', ['400 г брокколи', '1 л бульона', 'лук', '100 мл сливок'], ['Обжарь лук.', 'Добавь брокколи и бульон, вари до мягкости.', 'Пробей блендером и добавь сливки.']), ('Куриный суп с овощами', 'Очень просто', 'Суп', '45 мин', ['300 г курицы', 'морковь', 'картофель', 'лук', '1 л воды'], ['Отвари курицу.', 'Добавь овощи.', 'Вари до готовности.']), ('Минестроне', 'Средне', 'Суп', '45 мин', ['кабачок', 'морковь', 'фасоль', 'томаты', 'лук', '1 л бульона'], ['Обжарь овощи.', 'Добавь томаты, фасоль и бульон.', 'Вари до мягкости овощей.']), ('Рыбный суп', 'Просто', 'Суп', '35 мин', ['300 г белой рыбы', 'картофель', 'морковь', 'лук', '1 л воды'], ['Свари овощи до полуготовности.', 'Добавь рыбу.', 'Вари ещё 10–12 минут.']), ('Салат с тунцом и яйцом', 'Очень просто', 'Обед', '10 мин', ['тунец', '2 яйца', 'салат', 'огурец', 'помидоры'], ['Свари яйца.', 'Нарежь овощи.', 'Смешай всё с тунцом.']), ('Салат с авокадо и курицей', 'Просто', 'Обед', '20 мин', ['курица', 'авокадо', 'салат', 'помидоры', 'огурец'], ['Приготовь курицу.', 'Нарежь овощи и авокадо.', 'Смешай ингредиенты.']), ('Салат с нутом', 'Очень просто', 'Обед', '10 мин', ['нут', 'огурец', 'помидоры', 'лук', 'зелень'], ['Слей жидкость с нута.', 'Нарежь овощи.', 'Смешай всё с зеленью.']), ('Куриные шашлычки', 'Средне', 'Ужин', '35 мин', ['500 г курицы', 'перец', 'лук', 'паприка', 'масло'], ['Нарежь курицу и овощи.', 'Нанижи на шпажки.', 'Запекай или готовь на гриле до полной готовности.']), ('Индейка с овощами', 'Просто', 'Ужин', '30 мин', ['400 г индейки', 'брокколи', 'морковь', 'перец', 'соевый соус'], ['Нарежь индейку и овощи.', 'Обжарь индейку.', 'Добавь овощи и соус, готовь до мягкости.']), ('Треска с лимоном', 'Очень просто', 'Ужин', '25 мин', ['2 филе трески', 'лимон', 'чеснок', 'масло', 'зелень'], ['Выложи рыбу в форму.', 'Добавь лимон, чеснок и масло.', 'Запекай при 200°C около 15–18 минут.']), ('Креветки с чесноком', 'Просто', 'Ужин', '15 мин', ['300 г креветок', '3 зубчика чеснока', 'масло', 'лимон', 'зелень'], ['Обжарь чеснок.', 'Добавь креветки и готовь несколько минут.', 'Сбрызни лимоном и добавь зелень.']), ('Чили с фасолью', 'Просто', 'Ужин', '35 мин', ['фасоль', 'томаты', 'кукуруза', 'лук', 'перец', 'паприка'], ['Обжарь лук и перец.', 'Добавь томаты, фасоль и кукурузу.', 'Туши со специями 20 минут.']), ('Карри с нутом', 'Средне', 'Ужин', '35 мин', ['нут', 'кокосовое молоко', 'карри', 'томаты', 'лук', 'шпинат'], ['Обжарь лук со специями.', 'Добавь томаты, нут и кокосовое молоко.', 'Потуши и добавь шпинат в конце.']), ('Тофу с рисом терияки', 'Просто', 'Ужин', '30 мин', ['200 г тофу', '200 г риса', 'соевый соус', 'мёд', 'брокколи'], ['Свари рис.', 'Обжарь тофу.', 'Добавь соус и брокколи, подай с рисом.']), ('Овощное рагу', 'Очень просто', 'Ужин', '40 мин', ['картофель', 'кабачок', 'морковь', 'перец', 'томаты'], ['Нарежь овощи.', 'Обжарь часть овощей.', 'Добавь остальные и туши до мягкости.']), ('Запечённая курица с брокколи', 'Просто', 'Ужин', '35 мин', ['300 г курицы', '300 г брокколи', 'чеснок', 'масло', 'паприка'], ['Выложи всё в форму.', 'Добавь масло и специи.', 'Запекай при 200°C около 25 минут.']), ('Куриные фахитас', 'Средне', 'Ужин', '30 мин', ['300 г курицы', '2 тортильи', 'перец', 'лук', 'паприка'], ['Нарежь курицу и овощи.', 'Обжарь со специями.', 'Разложи по тортильям и сверни.']), ('Пита с фалафелем', 'Средне', 'Обед', '30 мин', ['фалафель', '2 питы', 'огурец', 'помидор', 'салат', 'йогуртовый соус'], ['Приготовь или разогрей фалафель.', 'Нарежь овощи.', 'Наполни питы и добавь соус.']), ('Запечённый батат', 'Очень просто', 'Гарнир', '40 мин', ['2 батата', '1 ст. л. масла', 'паприка', 'соль'], ['Нарежь батат.', 'Перемешай с маслом и специями.', 'Запекай при 200°C 30–35 минут.']), ('Киноа с овощами', 'Очень просто', 'Гарнир', '25 мин', ['150 г киноа', 'перец', 'кукуруза', 'морковь', 'зелень'], ['Промой и свари киноа.', 'Приготовь овощи.', 'Смешай и добавь зелень.']), ('Картофельные дольки с чесноком', 'Очень просто', 'Гарнир', '40 мин', ['500 г картофеля', 'чеснок', 'масло', 'паприка'], ['Нарежь картофель дольками.', 'Добавь масло, чеснок и специи.', 'Запекай до румяной корочки.']), ('Капустный салат', 'Очень просто', 'Гарнир', '10 мин', ['капуста', 'морковь', 'огурец', 'лимон', 'масло'], ['Нашинкуй овощи.', 'Добавь лимонный сок и масло.', 'Перемешай.']), ('Морковный хумус', 'Просто', 'Перекус', '20 мин', ['нут', '2 моркови', 'тахини', 'лимон', 'чеснок'], ['Запеки морковь до мягкости.', 'Пробей все ингредиенты блендером.', 'Подавай охлаждённым.']), ('Энергетические шарики', 'Очень просто', 'Перекус', '15 мин', ['овсянка', 'арахисовая паста', 'банан', 'корица'], ['Разомни банан.', 'Смешай все ингредиенты.', 'Сформируй шарики и охлади.']), ('Тост с творогом и ягодами', 'Очень просто', 'Перекус', '5 мин', ['2 ломтика хлеба', 'творог', 'ягоды', 'мёд по желанию'], ['Подрумянь хлеб.', 'Намажь творог.', 'Добавь ягоды и немного мёда.']), ('Попкорн с паприкой', 'Очень просто', 'Перекус', '10 мин', ['кукуруза для попкорна', '1 ч. л. масла', 'паприка', 'соль'], ['Приготовь попкорн.', 'Добавь масло и специи.', 'Перемешай.']), ('Запечённый нут с карри', 'Очень просто', 'Перекус', '35 мин', ['нут', 'масло', 'карри', 'соль'], ['Обсуши нут.', 'Смешай с маслом и карри.', 'Запекай при 200°C 25–30 минут.']), ('Клубничный смузи', 'Очень просто', 'Перекус', '5 мин', ['200 г клубники', 'банан', '200 мл йогурта'], ['Положи всё в блендер.', 'Взбей до однородности.', 'Подавай сразу.']), ('Какао-банановый смузи', 'Очень просто', 'Перекус', '5 мин', ['банан', '200 мл молока', '1 ч. л. какао', 'овсянка'], ['Положи ингредиенты в блендер.', 'Взбей до кремовой текстуры.', 'Подавай охлаждённым.']), ('Творожный десерт с какао', 'Очень просто', 'Десерт', '5 мин', ['200 г творога', '1 ч. л. какао', 'банан', 'ягоды'], ['Разомни банан.', 'Смешай с творогом и какао.', 'Добавь ягоды.']), ('Йогуртовое мороженое', 'Очень просто', 'Десерт', '10 мин + заморозка', ['300 г йогурта', 'ягоды', '1 ч. л. мёда'], ['Смешай йогурт с ягодами.', 'Разложи по формочкам.', 'Заморозь до плотной текстуры.']), ('Овсяное печенье с бананом', 'Просто', 'Десерт', '25 мин', ['2 банана', '120 г овсянки', 'корица', 'горсть орехов'], ['Разомни бананы.', 'Смешай с овсянкой и орехами.', 'Сформируй печенье и выпекай при 180°C 15–18 минут.']), ('Запечённая груша с орехами', 'Очень просто', 'Десерт', '25 мин', ['2 груши', 'орехи', 'корица', '1 ч. л. мёда'], ['Разрежь груши и удали сердцевину.', 'Добавь орехи и корицу.', 'Запекай при 180°C около 20 минут.']), ('Рисовый пудинг', 'Средне', 'Десерт', '40 мин', ['100 г риса', '500 мл молока', 'сахар', 'корица'], ['Вари рис в молоке на слабом огне.', 'Добавь сахар.', 'Подавай с корицей.']), ('Малиновый чиа-пудинг', 'Очень просто', 'Десерт', '5 мин + охлаждение', ['3 ст. л. чиа', '200 мл молока', '100 г малины', '1 ч. л. мёда'], ['Разомни часть малины.', 'Смешай с молоком и чиа.', 'Охлади минимум 2 часа и добавь оставшиеся ягоды.']), ('Домашняя гранола', 'Просто', 'Завтрак', '30 мин', ['200 г овсянки', 'орехи', 'семечки', '1 ст. л. мёда', '1 ст. л. масла'], ['Смешай ингредиенты.', 'Распредели тонким слоем.', 'Запекай при 170°C около 20 минут, перемешав в середине.']), ('Шакшука с фетой', 'Средне', 'Завтрак', '25 мин', ['4 яйца', '400 г томатов', 'перец', 'лук', '50 г феты'], ['Обжарь лук и перец.', 'Добавь томаты и специи.', 'Добавь яйца и фету, накрой и готовь до желаемой степени.']), ('Брускетта с томатами', 'Очень просто', 'Перекус', '10 мин', ['багет', '2 помидора', 'чеснок', 'базилик', 'масло'], ['Подрумянь хлеб.', 'Нарежь помидоры и смешай с базиликом.', 'Выложи на хлеб и добавь масло.']), ('Тёплый боул с киноа и овощами', 'Просто', 'Обед', '30 мин', ['150 г киноа', 'брокколи', 'морковь', 'нут', 'авокадо'], ['Свари киноа.', 'Запеки или обжарь овощи и нут.', 'Собери всё в миске и добавь авокадо.']), ('Лапша с овощами и яйцом', 'Просто', 'Обед', '20 мин', ['лапша', '2 яйца', 'морковь', 'перец', 'соевый соус'], ['Приготовь лапшу.', 'Обжарь овощи.', 'Добавь яйца, лапшу и соевый соус.']), ('Куриный рисовый боул', 'Просто', 'Обед', '30 мин', ['200 г риса', '300 г курицы', 'огурец', 'морковь', 'соевый соус'], ['Свари рис.', 'Приготовь курицу.', 'Собери боул с овощами и соусом.']), ('Запечённая цветная капуста', 'Очень просто', 'Гарнир', '30 мин', ['1 небольшая цветная капуста', 'масло', 'паприка', 'чеснок'], ['Раздели капусту на соцветия.', 'Смешай со специями и маслом.', 'Запекай при 200°C около 20–25 минут.']), ('Омлет со шпинатом и фетой', 'Просто', 'Завтрак', '15 мин', ['3 яйца', 'горсть шпината', '50 г феты', '1 ч. л. масла'], ['Взбей яйца.', 'Слегка обжарь шпинат.', 'Добавь яйца и фету, готовь до готовности.']), ('Ночная овсянка с яблоком', 'Очень просто', 'Завтрак', '5 мин + ночь', ['60 г овсянки', '150 мл йогурта', 'яблоко', 'корица', '1 ч. л. мёда'], ['Смешай овсянку и йогурт.', 'Добавь яблоко и корицу.', 'Оставь в холодильнике на ночь.']), ('Тост с арахисовой пастой и бананом', 'Очень просто', 'Завтрак', '5 мин', ['2 ломтика хлеба', 'арахисовая паста', '1 банан', 'корица'], ['Подрумянь хлеб.', 'Намажь арахисовую пасту.', 'Добавь банан и корицу.']), ('Яичные маффины с овощами', 'Просто', 'Завтрак', '25 мин', ['5 яиц', 'перец', 'шпинат', 'помидоры', 'сыр'], ['Взбей яйца и добавь овощи.', 'Разлей по формочкам.', 'Запекай при 180°C 15–18 минут.']), ('Булочка с яйцом и авокадо', 'Просто', 'Завтрак', '15 мин', ['1 булочка', '2 яйца', 'авокадо', 'салат'], ['Подрумянь булочку.', 'Приготовь яйца.', 'Собери с авокадо и салатом.']), ('Кускус с овощами и фетой', 'Очень просто', 'Обед', '15 мин', ['200 г кускуса', 'огурец', 'помидоры', '50 г феты', 'зелень'], ['Залей кускус горячей водой.', 'Нарежь овощи и фету.', 'Смешай и добавь зелень.']), ('Паста с тунцом и томатами', 'Просто', 'Обед', '25 мин', ['200 г пасты', '1 банка тунца', 'томаты', 'чеснок', 'зелень'], ['Отвари пасту.', 'Обжарь чеснок и томаты.', 'Добавь тунец и пасту, перемешай.']), ('Рис с курицей и брокколи', 'Просто', 'Обед', '30 мин', ['200 г риса', '300 г курицы', '300 г брокколи', 'соевый соус'], ['Свари рис.', 'Обжарь курицу.', 'Добавь брокколи и соус, подай с рисом.']), ('Чечевица с овощами', 'Просто', 'Обед', '35 мин', ['200 г чечевицы', 'морковь', 'перец', 'лук', 'томаты'], ['Свари чечевицу.', 'Обжарь овощи.', 'Добавь чечевицу и томаты, потуши 10 минут.']), ('Киноа с курицей и авокадо', 'Просто', 'Обед', '30 мин', ['150 г киноа', '250 г курицы', 'авокадо', 'огурец', 'лимон'], ['Свари киноа.', 'Приготовь курицу.', 'Собери боул с авокадо, огурцом и лимоном.']), ('Томатная паста с базиликом', 'Очень просто', 'Ужин', '20 мин', ['200 г пасты', '400 г томатов', 'чеснок', 'базилик', 'пармезан'], ['Отвари пасту.', 'Потуши томаты с чесноком.', 'Смешай с пастой и базиликом.']), ('Индейка с гречкой', 'Очень просто', 'Ужин', '30 мин', ['250 г индейки', '180 г гречки', 'лук', 'морковь'], ['Свари гречку.', 'Обжарь индейку с овощами.', 'Смешай и прогрей.']), ('Форель с картофелем', 'Просто', 'Ужин', '40 мин', ['2 филе форели', '400 г картофеля', 'лимон', 'зелень'], ['Нарежь картофель и запекай 20 минут.', 'Добавь рыбу и лимон.', 'Запекай ещё 15–18 минут.']), ('Треска с овощами на пару', 'Просто', 'Ужин', '25 мин', ['2 филе трески', 'брокколи', 'морковь', 'лимон'], ['Приготовь овощи на пару.', 'Добавь рыбу и готовь до полной готовности.', 'Подавай с лимоном.']), ('Креветки с рисом и овощами', 'Просто', 'Ужин', '25 мин', ['250 г креветок', '200 г риса', 'перец', 'горошек', 'соевый соус'], ['Свари рис.', 'Обжарь овощи и креветки.', 'Добавь рис и соус.']), ('Овощная лазанья', 'Средне', 'Ужин', '75 мин', ['листы лазаньи', 'кабачок', 'баклажан', 'томаты', 'сыр'], ['Обжарь овощи.', 'Выкладывай слоями овощи, соус и пасту.', 'Запекай при 180°C около 40 минут.']), ('Фаршированные перцы', 'Средне', 'Ужин', '60 мин', ['3 сладких перца', '250 г фарша', '150 г риса', 'томаты', 'сыр'], ['Свари рис и смешай с фаршем.', 'Наполни перцы начинкой.', 'Запекай с томатами при 190°C около 40 минут.']), ('Суп-пюре из кабачка', 'Очень просто', 'Суп', '30 мин', ['2 кабачка', 'лук', '700 мл бульона', '100 мл сливок'], ['Обжарь лук.', 'Добавь кабачок и бульон, вари до мягкости.', 'Пробей блендером и добавь сливки.']), ('Куриный суп с рисом', 'Очень просто', 'Суп', '40 мин', ['300 г курицы', '80 г риса', 'морковь', 'лук', '1 л воды'], ['Отвари курицу.', 'Добавь овощи и рис.', 'Вари до готовности риса и курицы.']), ('Грибной крем-суп', 'Просто', 'Суп', '35 мин', ['300 г шампиньонов', 'лук', '700 мл бульона', '100 мл сливок'], ['Обжарь грибы и лук.', 'Добавь бульон и вари 15 минут.', 'Измельчи блендером и добавь сливки.']), ('Суп с фрикадельками', 'Средне', 'Суп', '45 мин', ['300 г фарша', 'картофель', 'морковь', 'лук', '1 л воды'], ['Сформируй фрикадельки.', 'Отвари овощи.', 'Добавь фрикадельки и вари до готовности.']), ('Свекольный салат с фетой', 'Очень просто', 'Салат', '10 мин', ['2 варёные свёклы', '50 г феты', 'руккола', 'грецкие орехи'], ['Нарежь свёклу.', 'Добавь рукколу и фету.', 'Посыпь орехами и заправь маслом.']), ('Салат с курицей и кукурузой', 'Очень просто', 'Салат', '15 мин', ['250 г курицы', 'кукуруза', 'огурец', 'салат', 'йогуртовый соус'], ['Приготовь курицу.', 'Нарежь овощи.', 'Смешай всё с кукурузой и соусом.']), ('Салат с фасолью и авокадо', 'Очень просто', 'Салат', '10 мин', ['фасоль', 'авокадо', 'помидоры', 'кукуруза', 'лайм'], ['Нарежь авокадо и помидоры.', 'Добавь фасоль и кукурузу.', 'Заправь соком лайма.']), ('Салат с лососем и огурцом', 'Просто', 'Салат', '15 мин', ['150 г лосося', 'огурец', 'салат', 'авокадо', 'лимон'], ['Приготовь лосось.', 'Нарежь овощи.', 'Собери салат и добавь лимонный сок.']), ('Капрезе с базиликом', 'Очень просто', 'Салат', '10 мин', ['моцарелла', 'помидоры', 'базилик', 'оливковое масло'], ['Нарежь моцареллу и помидоры.', 'Чередуй их на тарелке.', 'Добавь базилик и масло.']), ('Запечённые овощи с фетой', 'Очень просто', 'Гарнир', '35 мин', ['кабачок', 'перец', 'помидоры', 'фета', 'масло'], ['Нарежь овощи.', 'Смешай с маслом.', 'Запекай при 200°C 25 минут и добавь фету.']), ('Пюре из цветной капусты', 'Просто', 'Гарнир', '25 мин', ['1 цветная капуста', '50 мл молока', '20 г масла', 'соль'], ['Отвари капусту до мягкости.', 'Пробей с молоком и маслом.', 'Посоли по вкусу.']), ('Рататуй', 'Средне', 'Гарнир', '60 мин', ['кабачок', 'баклажан', 'перец', 'томаты', 'лук'], ['Нарежь овощи.', 'Выложи слоями в форму.', 'Запекай при 190°C около 45 минут.']), ('Кукуруза на гриле', 'Очень просто', 'Гарнир', '15 мин', ['2 початка кукурузы', 'масло', 'паприка', 'соль'], ['Смажь кукурузу маслом.', 'Обжарь на гриле до румяных полосок.', 'Добавь паприку и соль.']), ('Хумус с запечённым перцем', 'Просто', 'Перекус', '15 мин', ['нут', '1 запечённый перец', 'тахини', 'лимон', 'чеснок'], ['Пробей все ингредиенты блендером.', 'Добавь немного воды до нужной текстуры.', 'Подавай с овощами или хлебом.']), ('Йогурт с гранолой и ягодами', 'Очень просто', 'Перекус', '5 мин', ['200 г йогурта', 'гранола', 'ягоды', 'банан'], ['Выложи йогурт в миску.', 'Добавь гранолу и фрукты.', 'Подавай сразу.']), ('Овощные роллы в тортилье', 'Очень просто', 'Перекус', '10 мин', ['2 тортильи', 'хумус', 'морковь', 'огурец', 'салат'], ['Смажь тортилью хумусом.', 'Добавь овощи и салат.', 'Сверни и нарежь.']), ('Мини-пиццы на тортилье', 'Просто', 'Перекус', '15 мин', ['2 тортильи', 'томатный соус', 'сыр', 'помидоры', 'орегано'], ['Смажь тортильи соусом.', 'Добавь сыр и овощи.', 'Запекай при 200°C 8–10 минут.']), ('Фруктовый салат с йогуртом', 'Очень просто', 'Десерт', '10 мин', ['яблоко', 'банан', 'киви', 'ягоды', 'йогурт'], ['Нарежь фрукты.', 'Смешай в миске.', 'Добавь йогурт перед подачей.']), ('Шоколадный чиа-пудинг', 'Очень просто', 'Десерт', '5 мин + охлаждение', ['3 ст. л. чиа', '200 мл молока', '1 ст. л. какао', '1 ч. л. мёда'], ['Смешай все ингредиенты.', 'Оставь на 10 минут и перемешай ещё раз.', 'Охлади минимум 2 часа.']), ('Запечённые яблоки с творогом', 'Просто', 'Десерт', '30 мин', ['2 яблока', '100 г творога', 'корица', 'орехи'], ['Удалить сердцевину яблок.', 'Наполни творогом и посыпь корицей.', 'Запекай при 180°C около 20 минут.']), ('Кокосовые овсяные батончики', 'Просто', 'Десерт', '30 мин', ['150 г овсянки', '50 г кокосовой стружки', 'банан', '1 ст. л. мёда'], ['Разомни банан и смешай всё.', 'Утрамбуй в форме.', 'Запекай при 180°C 20 минут.']), ('Малиновый смузи-боул', 'Очень просто', 'Завтрак', '10 мин', ['150 г малины', '1 банан', '150 г йогурта', 'гранола'], ['Взбей ягоды, банан и йогурт.', 'Перелей в миску.', 'Добавь гранолу сверху.']), ('Творожные маффины', 'Средне', 'Завтрак', '30 мин', ['200 г творога', '2 яйца', '80 г муки', '1 ч. л. разрыхлителя', 'ягоды'], ['Смешай все ингредиенты.', 'Разложи по формочкам.', 'Выпекай при 180°C около 20 минут.']), ('Куриные наггетсы в духовке', 'Средне', 'Ужин', '35 мин', ['400 г курицы', '1 яйцо', 'панировочные сухари', 'паприка'], ['Нарежь курицу.', 'Обмакни в яйцо и сухари со специями.', 'Запекай при 200°C около 20 минут до полной готовности.']), ('Паста с креветками и томатами', 'Средне', 'Ужин', '30 мин', ['200 г пасты', '250 г креветок', 'томаты', 'чеснок', 'базилик'], ['Отвари пасту.', 'Обжарь чеснок и креветки.', 'Добавь томаты и пасту, прогрей вместе.']), ('Нутовые котлеты', 'Средне', 'Ужин', '35 мин', ['300 г нута', '1 яйцо', 'лук', 'панировочные сухари', 'петрушка'], ['Разомни нут.', 'Смешай с остальными ингредиентами.', 'Сформируй котлеты и обжарь или запеки до готовности.']), ('Овощная фриттата', 'Средне', 'Ужин', '30 мин', ['5 яиц', 'кабачок', 'перец', 'лук', '50 г сыра'], ['Обжарь овощи.', 'Залей взбитыми яйцами и добавь сыр.', 'Готовь под крышкой или запеки до полной готовности.']), ('Гречневые блины', 'Средне', 'Завтрак', '25 мин', ['100 г гречневой муки', '1 яйцо', '200 мл молока', 'щепотка соли'], ['Смешай тесто.', 'Разогрей сковороду.', 'Испеки тонкие блины с двух сторон.']), ('Смузи с манго и йогуртом', 'Очень просто', 'Перекус', '5 мин', ['1 манго', '200 г йогурта', '100 мл воды', 'лайм'], ['Очисти манго.', 'Взбей всё блендером.', 'Добавь сок лайма по вкусу.']), ('Тост с хумусом и овощами', 'Очень просто', 'Перекус', '5 мин', ['2 ломтика хлеба', 'хумус', 'огурец', 'помидор', 'зелень'], ['Подрумянь хлеб.', 'Намажь хумус.', 'Добавь овощи и зелень.']), ('Запечённые фалафели', 'Средне', 'Ужин', '40 мин', ['300 г нута', 'лук', 'чеснок', 'петрушка', 'кумин'], ['Пробей ингредиенты в блендере.', 'Сформируй шарики.', 'Запекай при 200°C 20–25 минут, перевернув в середине.']), ('Овощной вок с тофу', 'Средне', 'Ужин', '25 мин', ['200 г тофу', 'брокколи', 'морковь', 'перец', 'соевый соус'], ['Нарежь тофу и овощи.', 'Обжарь на сильном огне.', 'Добавь соевый соус и готовь ещё несколько минут.'])]


# Расширенная база фитнеса LIVO
FITNESS_GOALS = {
    "muscle": "Набор мышц",
    "strength": "Сила",
    "fatloss": "Снижение веса",
    "fitness": "Общая форма",
    "endurance": "Выносливость",
}
FITNESS_LEVELS = {"beginner": "Новичок", "intermediate": "Средний", "advanced": "Продвинутый"}

FITNESS_LIBRARY = [
    # name, muscles, equipment, levels, goals, detail
    ("Жим лёжа со штангой", ["Грудь"], ["Штанга", "Скамья"], ["intermediate","advanced"], ["muscle","strength"], "3–4 × 6–12"),
    ("Жим гантелей лёжа", ["Грудь"], ["Гантели", "Скамья"], ["beginner","intermediate","advanced"], ["muscle","fitness"], "3–4 × 8–12"),
    ("Жим гантелей на наклонной скамье", ["Грудь"], ["Гантели", "Скамья"], ["intermediate","advanced"], ["muscle"], "3 × 8–12"),
    ("Отжимания", ["Грудь","Трицепс"], ["Собственный вес"], ["beginner","intermediate","advanced"], ["muscle","fitness","fatloss"], "3 × 8–20"),
    ("Отжимания с узкой постановкой рук", ["Грудь","Трицепс"], ["Собственный вес"], ["intermediate","advanced"], ["strength","muscle"], "3 × 8–15"),
    ("Разводка гантелей", ["Грудь"], ["Гантели","Скамья"], ["beginner","intermediate"], ["muscle"], "3 × 10–15"),
    ("Сведение рук в тренажёре", ["Грудь"], ["Тренажёр"], ["beginner","intermediate"], ["muscle"], "3 × 10–15"),
    ("Подтягивания", ["Спина","Бицепс"], ["Турник"], ["intermediate","advanced"], ["strength","muscle"], "3–4 × 5–12"),
    ("Подтягивания с резинкой", ["Спина","Бицепс"], ["Турник","Резинка"], ["beginner","intermediate"], ["fitness","muscle"], "3 × 5–12"),
    ("Тяга верхнего блока", ["Спина"], ["Тренажёр","Кроссовер"], ["beginner","intermediate","advanced"], ["muscle","fitness"], "3–4 × 8–12"),
    ("Тяга горизонтального блока", ["Спина"], ["Тренажёр","Кроссовер"], ["beginner","intermediate","advanced"], ["muscle"], "3 × 8–12"),
    ("Тяга штанги в наклоне", ["Спина"], ["Штанга"], ["intermediate","advanced"], ["strength","muscle"], "3–4 × 6–12"),
    ("Тяга гантели одной рукой", ["Спина"], ["Гантели","Скамья"], ["beginner","intermediate","advanced"], ["muscle"], "3 × 8–12"),
    ("Тяга Т-грифа", ["Спина"], ["Штанга","Тренажёр"], ["intermediate","advanced"], ["strength","muscle"], "3 × 8–12"),
    ("Гиперэкстензия", ["Спина","Ягодицы"], ["Тренажёр"], ["beginner","intermediate"], ["fitness"], "3 × 10–15"),
    ("Приседания с собственным весом", ["Квадрицепс","Ягодицы"], ["Собственный вес"], ["beginner"], ["fitness","fatloss"], "3 × 12–20"),
    ("Приседания со штангой", ["Квадрицепс","Ягодицы"], ["Штанга"], ["intermediate","advanced"], ["strength","muscle"], "3–4 × 6–12"),
    ("Фронтальные приседания", ["Квадрицепс","Ягодицы"], ["Штанга"], ["intermediate","advanced"], ["strength","muscle"], "3 × 6–10"),
    ("Гакк-присед", ["Квадрицепс","Ягодицы"], ["Тренажёр"], ["intermediate","advanced"], ["muscle"], "3 × 8–12"),
    ("Жим ногами", ["Квадрицепс","Ягодицы"], ["Тренажёр"], ["beginner","intermediate","advanced"], ["muscle","strength"], "3–4 × 8–15"),
    ("Разгибание ног", ["Квадрицепс"], ["Тренажёр"], ["beginner","intermediate"], ["muscle"], "3 × 10–15"),
    ("Болгарские сплит-приседы", ["Квадрицепс","Ягодицы"], ["Гантели","Скамья"], ["intermediate","advanced"], ["muscle","fitness"], "3 × 8–12 на ногу"),
    ("Выпады с гантелями", ["Квадрицепс","Ягодицы"], ["Гантели"], ["beginner","intermediate","advanced"], ["fitness","muscle","fatloss"], "3 × 8–12 на ногу"),
    ("Шаги на платформу", ["Квадрицепс","Ягодицы"], ["Скамья"], ["beginner","intermediate"], ["fitness","fatloss"], "3 × 10 на ногу"),
    ("Румынская тяга", ["Бицепс бедра","Ягодицы"], ["Штанга"], ["intermediate","advanced"], ["strength","muscle"], "3 × 8–12"),
    ("Сгибание ног лёжа", ["Бицепс бедра"], ["Тренажёр"], ["beginner","intermediate"], ["muscle"], "3 × 10–15"),
    ("Ягодичный мост", ["Ягодицы"], ["Собственный вес","Штанга"], ["beginner","intermediate","advanced"], ["muscle","fitness"], "3–4 × 10–15"),
    ("Отведение ноги назад", ["Ягодицы"], ["Кроссовер","Резинка"], ["beginner","intermediate"], ["muscle"], "3 × 12–15"),
    ("Подъём на носки стоя", ["Икры"], ["Тренажёр","Гантели"], ["beginner","intermediate","advanced"], ["muscle","fitness"], "3–4 × 12–20"),
    ("Жим гантелей сидя", ["Плечи"], ["Гантели","Скамья"], ["beginner","intermediate","advanced"], ["muscle","strength"], "3 × 8–12"),
    ("Жим штанги над головой", ["Плечи","Трицепс"], ["Штанга"], ["intermediate","advanced"], ["strength","muscle"], "3 × 6–10"),
    ("Разведения гантелей в стороны", ["Плечи"], ["Гантели"], ["beginner","intermediate"], ["muscle"], "3 × 10–15"),
    ("Обратная бабочка", ["Плечи","Спина"], ["Тренажёр"], ["beginner","intermediate"], ["muscle"], "3 × 10–15"),
    ("Тяга каната к лицу", ["Плечи","Спина"], ["Кроссовер"], ["beginner","intermediate"], ["fitness","muscle"], "3 × 10–15"),
    ("Подъём штанги на бицепс", ["Бицепс"], ["Штанга"], ["beginner","intermediate","advanced"], ["muscle","strength"], "3 × 8–12"),
    ("Сгибание рук с гантелями", ["Бицепс"], ["Гантели"], ["beginner","intermediate","advanced"], ["muscle"], "3 × 8–12"),
    ("Молотковые сгибания", ["Бицепс","Предплечья"], ["Гантели"], ["beginner","intermediate"], ["muscle"], "3 × 8–12"),
    ("Разгибание рук на блоке", ["Трицепс"], ["Кроссовер"], ["beginner","intermediate","advanced"], ["muscle"], "3 × 10–15"),
    ("Французский жим", ["Трицепс"], ["Штанга","Гантели"], ["intermediate","advanced"], ["muscle"], "3 × 8–12"),
    ("Разгибание руки из-за головы", ["Трицепс"], ["Гантели"], ["beginner","intermediate"], ["muscle"], "3 × 10–15"),
    ("Скручивания", ["Пресс"], ["Собственный вес","Коврик"], ["beginner","intermediate","advanced"], ["fitness","fatloss"], "3 × 12–20"),
    ("Планка", ["Кор"], ["Собственный вес","Коврик"], ["beginner","intermediate","advanced"], ["fitness","endurance"], "3 × 30–60 сек"),
    ("Боковая планка", ["Кор"], ["Собственный вес","Коврик"], ["beginner","intermediate"], ["fitness","endurance"], "3 × 20–45 сек"),
    ("Подъём коленей в упоре", ["Пресс"], ["Брусья"], ["intermediate","advanced"], ["strength","fitness"], "3 × 10–15"),
    ("Подъём ног в висе", ["Пресс","Кор"], ["Турник"], ["intermediate","advanced"], ["strength","muscle"], "3 × 8–15"),
    ("Ролик для пресса", ["Пресс","Кор"], ["Аб-роллер"], ["intermediate","advanced"], ["strength"], "3 × 6–15"),
    ("Берпи", ["Всё тело"], ["Собственный вес"], ["intermediate","advanced"], ["fatloss","endurance"], "3 × 8–15"),
    ("Прыжки на тумбу", ["Ноги","Всё тело"], ["Плио-тумба"], ["intermediate","advanced"], ["endurance","fitness"], "3 × 6–12"),
    ("Jumping jacks", ["Всё тело"], ["Собственный вес"], ["beginner","intermediate"], ["fatloss","endurance"], "3 × 30–60 сек"),
    ("Mountain climbers", ["Пресс","Всё тело"], ["Собственный вес","Коврик"], ["beginner","intermediate","advanced"], ["fatloss","endurance"], "3 × 30–45 сек"),
    ("Беговая дорожка", ["Кардио"], ["Кардио-тренажёр"], ["beginner","intermediate","advanced"], ["fatloss","endurance","fitness"], "15–30 мин"),
    ("Велотренажёр", ["Кардио","Ноги"], ["Кардио-тренажёр"], ["beginner","intermediate","advanced"], ["fatloss","endurance"], "15–30 мин"),
    ("Эллиптический тренажёр", ["Кардио","Ноги"], ["Кардио-тренажёр"], ["beginner","intermediate","advanced"], ["fatloss","endurance"], "15–30 мин"),
    ("Гребной тренажёр", ["Кардио","Спина","Ноги"], ["Кардио-тренажёр"], ["beginner","intermediate","advanced"], ["endurance","fatloss"], "10–20 мин"),
    ("Степпер", ["Кардио","Ноги"], ["Кардио-тренажёр"], ["beginner","intermediate"], ["fatloss","endurance"], "10–20 мин"),
    ("Скакалка", ["Кардио","Икры"], ["Скакалка"], ["beginner","intermediate","advanced"], ["fatloss","endurance"], "5–15 мин"),
    ("Battle ropes", ["Всё тело","Плечи"], ["Battle ropes"], ["intermediate","advanced"], ["endurance","fatloss"], "6 × 20–30 сек"),
    ("Фермерская прогулка", ["Предплечья","Кор","Ноги"], ["Гантели"], ["beginner","intermediate","advanced"], ["strength","fitness"], "3 × 30–60 м"),
    ("Турецкий подъём", ["Всё тело","Кор"], ["Гантели"], ["advanced"], ["strength","fitness"], "3 × 3–5 на сторону"),
    ("Свинг с гирей", ["Ягодицы","Бицепс бедра","Кор"], ["Гиря"], ["intermediate","advanced"], ["strength","endurance","fatloss"], "3 × 12–20"),
    ("Goblet squat", ["Квадрицепс","Ягодицы"], ["Гиря","Гантели"], ["beginner","intermediate"], ["fitness","muscle"], "3 × 10–15"),
    ("Отжимания на брусьях", ["Грудь","Трицепс"], ["Брусья"], ["intermediate","advanced"], ["strength","muscle"], "3 × 6–12"),
    ("Отжимания с узкой постановкой рук", ["Грудь","Трицепс"], ["Собственный вес"], ["beginner","intermediate","advanced"], ["fitness","muscle","strength"], "3 × 8–20"),
    ("Отжимания с широкой постановкой рук", ["Грудь"], ["Собственный вес"], ["beginner","intermediate"], ["fitness","muscle"], "3 × 8–20"),
    ("Жим штанги узким хватом", ["Грудь","Трицепс"], ["Штанга","Скамья"], ["intermediate","advanced"], ["strength","muscle"], "3–4 × 6–10"),
    ("Жим гантелей нейтральным хватом", ["Грудь","Трицепс"], ["Гантели","Скамья"], ["beginner","intermediate"], ["muscle","fitness"], "3 × 8–12"),
    ("Кроссовер сверху вниз", ["Грудь"], ["Кроссовер"], ["beginner","intermediate"], ["muscle"], "3 × 10–15"),
    ("Пуловер с гантелью", ["Грудь","Спина"], ["Гантели","Скамья"], ["intermediate"], ["muscle"], "3 × 10–15"),
    ("Тяга Т-грифа", ["Спина"], ["Тренажёр","Штанга"], ["intermediate","advanced"], ["strength","muscle"], "3–4 × 6–12"),
    ("Тяга гантелей лёжа на наклонной скамье", ["Спина"], ["Гантели","Скамья"], ["intermediate"], ["muscle"], "3 × 8–12"),
    ("Пуловер на верхнем блоке", ["Спина"], ["Кроссовер"], ["intermediate"], ["muscle"], "3 × 10–15"),
    ("Подтягивания обратным хватом", ["Спина","Бицепс"], ["Турник"], ["intermediate","advanced"], ["strength","muscle"], "3–4 × 5–12"),
    ("Тяга нижнего блока узким хватом", ["Спина","Бицепс"], ["Кроссовер","Тренажёр"], ["beginner","intermediate"], ["muscle","fitness"], "3 × 8–12"),
    ("Шраги с гантелями", ["Плечи","Спина"], ["Гантели"], ["beginner","intermediate"], ["strength","muscle"], "3 × 10–15"),
    ("Жим Арнольда", ["Плечи"], ["Гантели","Скамья"], ["intermediate"], ["muscle","strength"], "3 × 8–12"),
    ("Подъём гантелей перед собой", ["Плечи"], ["Гантели"], ["beginner","intermediate"], ["fitness","muscle"], "3 × 10–15"),
    ("Разведения в наклоне", ["Плечи"], ["Гантели","Скамья"], ["beginner","intermediate"], ["muscle"], "3 × 10–15"),
    ("Сгибание рук на скамье Скотта", ["Бицепс"], ["Тренажёр","Штанга"], ["intermediate"], ["muscle"], "3 × 8–12"),
    ("Сгибание рук на нижнем блоке", ["Бицепс"], ["Кроссовер"], ["beginner","intermediate"], ["muscle"], "3 × 10–15"),
    ("Концентрированный подъём на бицепс", ["Бицепс"], ["Гантели","Скамья"], ["beginner","intermediate"], ["muscle"], "3 × 10–12"),
    ("Разгибание рук над головой на блоке", ["Трицепс"], ["Кроссовер"], ["intermediate"], ["muscle"], "3 × 10–15"),
    ("Отжимания от скамьи", ["Трицепс"], ["Скамья"], ["beginner","intermediate"], ["fitness","muscle"], "3 × 8–15"),
    ("Разгибание руки на блоке одной рукой", ["Трицепс"], ["Кроссовер"], ["beginner","intermediate"], ["muscle"], "3 × 10–15"),
    ("Фронтальные приседания", ["Квадрицепс","Ноги","Кор"], ["Штанга"], ["intermediate","advanced"], ["strength","muscle"], "3–4 × 5–10"),
    ("Болгарские сплит-приседы", ["Квадрицепс","Ягодицы"], ["Гантели","Скамья"], ["intermediate","advanced"], ["muscle","fitness"], "3 × 8–12 на ногу"),
    ("Шаги на платформу", ["Квадрицепс","Ягодицы"], ["Плио-тумба"], ["beginner","intermediate"], ["fitness","fatloss"], "3 × 10 на ногу"),
    ("Приседания с паузой", ["Квадрицепс","Ягодицы"], ["Собственный вес","Штанга"], ["beginner","intermediate","advanced"], ["strength","fitness"], "3 × 8–12"),
    ("Сумо-приседания", ["Ягодицы","Квадрицепс"], ["Гантели","Гиря"], ["beginner","intermediate"], ["fitness","muscle"], "3 × 10–15"),
    ("Отведение ноги назад в кроссовере", ["Ягодицы"], ["Кроссовер"], ["beginner","intermediate"], ["muscle","fitness"], "3 × 12–15"),
    ("Разведение ног в тренажёре", ["Ягодицы"], ["Тренажёр"], ["beginner","intermediate"], ["muscle"], "3 × 12–20"),
    ("Сгибание ног сидя", ["Бицепс бедра"], ["Тренажёр"], ["beginner","intermediate"], ["muscle"], "3 × 10–15"),
    ("Доброе утро", ["Бицепс бедра","Ягодицы","Кор"], ["Штанга"], ["intermediate","advanced"], ["strength","muscle"], "3 × 8–12"),
    ("Подъём на носки сидя", ["Икры"], ["Тренажёр"], ["beginner","intermediate"], ["muscle"], "3–4 × 12–20"),
    ("Подъём на носки одной ногой", ["Икры"], ["Собственный вес"], ["beginner","intermediate"], ["fitness","muscle"], "3 × 12–20"),
    ("Dead bug", ["Кор","Пресс"], ["Коврик"], ["beginner","intermediate"], ["fitness"], "3 × 8–12 на сторону"),
    ("Bird dog", ["Кор","Спина"], ["Коврик"], ["beginner","intermediate"], ["fitness"], "3 × 8–12 на сторону"),
    ("Боковая планка", ["Кор","Пресс"], ["Коврик"], ["beginner","intermediate","advanced"], ["fitness","endurance"], "3 × 20–60 сек на сторону"),
    ("Русские скручивания", ["Пресс","Кор"], ["Коврик","Гантели"], ["intermediate"], ["fitness","endurance"], "3 × 12–20"),
    ("Складка на пресс", ["Пресс","Кор"], ["Коврик"], ["intermediate","advanced"], ["fitness"], "3 × 8–15"),
    ("Mountain climbers", ["Пресс","Кардио","Всё тело"], ["Собственный вес"], ["beginner","intermediate","advanced"], ["fatloss","endurance","fitness"], "3 × 30–45 сек"),
    ("Jumping jacks", ["Кардио","Всё тело"], ["Собственный вес"], ["beginner","intermediate","advanced"], ["fatloss","endurance"], "3 × 30–60 сек"),
    ("Высокие колени", ["Кардио","Ноги"], ["Собственный вес"], ["beginner","intermediate","advanced"], ["fatloss","endurance"], "3 × 30–60 сек"),
    ("Боковые прыжки", ["Кардио","Ноги","Ягодицы"], ["Собственный вес"], ["intermediate","advanced"], ["fatloss","endurance"], "3 × 30 сек"),
    ("Медвежья ходьба", ["Всё тело","Кор","Плечи"], ["Собственный вес"], ["intermediate","advanced"], ["fitness","endurance"], "3 × 20–30 м"),
    ("Толчок гири", ["Плечи","Ноги","Всё тело"], ["Гиря"], ["intermediate","advanced"], ["strength","endurance"], "3 × 8–12 на руку"),
    ("Рывок гири", ["Плечи","Ягодицы","Всё тело"], ["Гиря"], ["advanced"], ["strength","endurance"], "3 × 6–10 на руку"),
    ("Тяга гири к подбородку", ["Плечи","Спина"], ["Гиря"], ["intermediate"], ["muscle","strength"], "3 × 8–12"),
    ("Тяга резинки к поясу", ["Спина","Бицепс"], ["Резинка"], ["beginner","intermediate"], ["fitness","muscle"], "3 × 12–20"),
    ("Разведение резинки", ["Плечи","Верх спины"], ["Резинка"], ["beginner","intermediate"], ["fitness"], "3 × 12–20"),
    ("Ягодичный мост на одной ноге", ["Ягодицы","Бицепс бедра"], ["Коврик"], ["intermediate"], ["muscle","fitness"], "3 × 10–15 на ногу"),
    ("Изометрический присед у стены", ["Квадрицепс","Ноги"], ["Собственный вес"], ["beginner","intermediate"], ["fitness","endurance"], "3 × 30–60 сек"),
    ("Выпады назад", ["Квадрицепс","Ягодицы"], ["Собственный вес","Гантели"], ["beginner","intermediate"], ["fitness","muscle"], "3 × 8–12 на ногу"),
    ("Выпады вперёд", ["Квадрицепс","Ягодицы"], ["Собственный вес","Гантели"], ["beginner","intermediate"], ["fitness","muscle"], "3 × 8–12 на ногу"),
    ("Ходьба на дорожке под наклоном", ["Кардио","Ноги"], ["Кардио-тренажёр"], ["beginner","intermediate","advanced"], ["fatloss","endurance"], "15–30 мин"),
    ("Интервалы на велотренажёре", ["Кардио","Ноги"], ["Кардио-тренажёр"], ["intermediate","advanced"], ["fatloss","endurance"], "10–20 мин"),
    ("Интервалы на гребном тренажёре", ["Кардио","Спина","Ноги"], ["Кардио-тренажёр"], ["intermediate","advanced"], ["fatloss","endurance"], "10–20 мин"),

]

FITNESS_MUSCLES = ["Грудь","Спина","Плечи","Бицепс","Трицепс","Пресс","Кор","Квадрицепс","Ягодицы","Бицепс бедра","Икры","Ноги","Всё тело","Кардио","Предплечья"]
FITNESS_EQUIPMENT = ["Собственный вес","Гантели","Штанга","Тренажёр","Кроссовер","Турник","Брусья","Скамья","Коврик","Кардио-тренажёр","Резинка","Гиря","Скакалка","Battle ropes","Аб-роллер","Плио-тумба"]

def _fitness_exercises(goal, level, selected_muscles, selected_equipment):
    result = []
    for name, muscles, equipment, levels, goals, detail in FITNESS_LIBRARY:
        if level and level not in levels:
            continue
        if goal and goal not in goals:
            continue
        if selected_muscles and not any(m in muscles for m in selected_muscles):
            continue
        if selected_equipment and not any(e in equipment for e in selected_equipment):
            continue
        result.append({"name": name, "muscles": ", ".join(muscles), "equipment": ", ".join(equipment), "detail": detail})
    return result

WORKOUT_PLANS = [
    ("Фулбади для новичка", "beginner", ["fitness"], 30, ["Приседания с собственным весом","Отжимания","Тяга верхнего блока","Ягодичный мост","Планка","Велотренажёр"]),
    ("Фулбади с гантелями", "beginner", ["muscle","fitness"], 40, ["Goblet squat","Жим гантелей лёжа","Тяга гантели одной рукой","Жим гантелей сидя","Молотковые сгибания","Планка"]),
    ("Сила: верх тела", "intermediate", ["strength"], 50, ["Жим лёжа со штангой","Подтягивания","Тяга штанги в наклоне","Жим штанги над головой","Французский жим"]),
    ("Ноги и ягодицы", "intermediate", ["muscle","fitness"], 50, ["Приседания со штангой","Румынская тяга","Болгарские сплит-приседы","Ягодичный мост","Подъём на носки стоя"]),
    ("Грудь и трицепс", "intermediate", ["muscle"], 45, ["Жим гантелей лёжа","Жим гантелей на наклонной скамье","Отжимания с узкой постановкой рук","Разводка гантелей","Разгибание рук на блоке"]),
    ("Спина и бицепс", "intermediate", ["muscle"], 45, ["Подтягивания с резинкой","Тяга верхнего блока","Тяга горизонтального блока","Тяга гантели одной рукой","Сгибание рук с гантелями"]),
    ("Кардио для снижения веса", "beginner", ["fatloss","endurance"], 30, ["Беговая дорожка","Велотренажёр","Jumping jacks","Mountain climbers","Скакалка"]),
    ("HIIT без оборудования", "intermediate", ["fatloss","endurance"], 25, ["Берпи","Jumping jacks","Mountain climbers","Приседания с собственным весом","Планка"]),
    ("Выносливость: кардио", "intermediate", ["endurance"], 45, ["Гребной тренажёр","Эллиптический тренажёр","Скакалка","Беговая дорожка"]),
    ("Плечи и руки", "beginner", ["muscle","fitness"], 35, ["Жим гантелей сидя","Разведения гантелей в стороны","Сгибание рук с гантелями","Разгибание руки из-за головы","Планка"]),
    ("Кор и пресс", "beginner", ["fitness","endurance"], 20, ["Скручивания","Планка","Боковая планка","Mountain climbers"]),
    ("Сила ног", "advanced", ["strength"], 55, ["Приседания со штангой","Фронтальные приседания","Румынская тяга","Болгарские сплит-приседы","Подъём на носки стоя"]),
    ("Атлетическая тренировка", "advanced", ["fitness","endurance"], 45, ["Прыжки на тумбу","Battle ropes","Свинг с гирей","Фермерская прогулка","Берпи"]),
    ("Домашняя тренировка 30 минут", "beginner", ["fitness","fatloss"], 30, ["Приседания с собственным весом","Отжимания","Выпады с гантелями","Ягодичный мост","Планка","Jumping jacks"]),
    ("Гиря: всё тело", "intermediate", ["strength","endurance"], 35, ["Свинг с гирей","Goblet squat","Фермерская прогулка","Турецкий подъём","Планка"]),
    ("Мобильность и лёгкая форма", "beginner", ["fitness"], 25, ["Приседания с собственным весом","Шаги на платформу","Ягодичный мост","Планка","Велотренажёр"]),
    ("Верх тела для новичка", "beginner", ["fitness","muscle"], 30, ["Отжимания","Тяга резинки к поясу","Жим гантелей сидя","Сгибание рук с гантелями","Разгибание рук на блоке"]),
    ("Низ тела для новичка", "beginner", ["fitness","muscle"], 30, ["Приседания с собственным весом","Выпады назад","Ягодичный мост","Подъём на носки одной ногой","Изометрический присед у стены"]),
    ("Грудь дома", "beginner", ["muscle","fitness"], 25, ["Отжимания","Отжимания с широкой постановкой рук","Отжимания с узкой постановкой рук","Планка"]),
    ("Спина дома с резинкой", "beginner", ["fitness","muscle"], 30, ["Тяга резинки к поясу","Разведение резинки","Bird dog","Планка"]),
    ("Ягодицы дома", "beginner", ["muscle","fitness"], 30, ["Ягодичный мост","Ягодичный мост на одной ноге","Выпады назад","Сумо-приседания"]),
    ("Сильные плечи", "intermediate", ["strength","muscle"], 40, ["Жим Арнольда","Разведения гантелей в стороны","Подъём гантелей перед собой","Тяга каната к лицу","Шраги с гантелями"]),
    ("Руки: бицепс + трицепс", "intermediate", ["muscle"], 40, ["Сгибание рук на скамье Скотта","Молотковые сгибания","Сгибание рук на нижнем блоке","Разгибание рук над головой на блоке","Разгибание руки на блоке одной рукой"]),
    ("Ноги с гантелями", "intermediate", ["muscle","strength"], 45, ["Goblet squat","Болгарские сплит-приседы","Румынская тяга","Выпады вперёд","Подъём на носки стоя"]),
    ("Ягодицы и задняя поверхность бедра", "intermediate", ["muscle"], 45, ["Румынская тяга","Ягодичный мост на одной ноге","Сгибание ног сидя","Доброе утро","Отведение ноги назад в кроссовере"]),
    ("Кор 25 минут", "intermediate", ["fitness","endurance"], 25, ["Dead bug","Боковая планка","Русские скручивания","Складка на пресс","Mountain climbers"]),
    ("HIIT 20 минут", "advanced", ["fatloss","endurance"], 20, ["Берпи","Высокие колени","Боковые прыжки","Mountain climbers","Jumping jacks"]),
    ("Гиря: сила и мощность", "advanced", ["strength","endurance"], 40, ["Свинг с гирей","Толчок гири","Рывок гири","Goblet squat","Фермерская прогулка"]),
    ("Силовая тренировка всего тела", "advanced", ["strength","muscle"], 55, ["Приседания со штангой","Жим лёжа со штангой","Тяга штанги в наклоне","Жим штанги над головой","Румынская тяга"]),
    ("Кардио интервалы", "advanced", ["fatloss","endurance"], 30, ["Интервалы на велотренажёре","Интервалы на гребном тренажёре","Скакалка","Высокие колени"]),
    ("Мобильность + кор", "beginner", ["fitness"], 25, ["Bird dog","Dead bug","Боковая планка","Ягодичный мост","Приседания с собственным весом"]),

]


def _slug(text):
    import re
    value = re.sub(r"[^a-zA-Z0-9а-яА-ЯёЁ]+", "-", text.lower()).strip("-")
    return value or "item"

# Local, dependency-free cover images. Generated once so cards never depend on external poster services.
def _ensure_local_posters():
    from html import escape
    posters_dir = os.path.join(BASE_DIR, "static", "posters")
    os.makedirs(posters_dir, exist_ok=True)
    def make_svg(title, subtitle, emoji, filename, hue):
        path = os.path.join(posters_dir, filename)
        if os.path.exists(path):
            return
        title_safe = escape(title)
        subtitle_safe = escape(subtitle)
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 900">
<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#090b18"/><stop offset="0.55" stop-color="{hue}"/><stop offset="1" stop-color="#050509"/></linearGradient><radialGradient id="r"><stop stop-color="#ffffff" stop-opacity=".18"/><stop offset="1" stop-color="#ffffff" stop-opacity="0"/></radialGradient></defs>
<rect width="600" height="900" rx="28" fill="url(#g)"/><circle cx="470" cy="180" r="260" fill="url(#r)"/><circle cx="120" cy="730" r="190" fill="#8b5cf6" opacity=".12"/>
<text x="300" y="320" text-anchor="middle" font-size="120">{emoji}</text>
<text x="300" y="570" text-anchor="middle" fill="#fff" font-family="Arial,sans-serif" font-size="38" font-weight="800">{title_safe}</text>
<text x="300" y="625" text-anchor="middle" fill="#c6c9d8" font-family="Arial,sans-serif" font-size="22">{subtitle_safe}</text>
<text x="300" y="820" text-anchor="middle" fill="#f1c96b" font-family="Arial,sans-serif" font-size="18" font-weight="700">LIVO • ENTERTAINMENT</text>
</svg>'''
        Path(path).write_text(svg, encoding='utf-8')
    hues = ['#32106d','#182f64','#5b1837','#3a1f72','#163f46','#6b2b12']
    for i, item in enumerate(MOVIES):
        fn=f"movie-{i}-{_slug(item['title'])}.svg"
        make_svg(item['title'], f"{item['year']} • {item['genre']}", '🎬', fn, hues[i % len(hues)])
        item['poster'] = f"/static/posters/{fn}"
    for i, item in enumerate(GAMES):
        fn=f"game-{i}-{_slug(item['title'])}.svg"
        make_svg(item['title'], f"{item['year']} • {item['genre']}", '🎮', fn, hues[(i+2) % len(hues)])
        item['poster'] = f"/static/posters/{fn}"

_ensure_local_posters()


def _recipe_cost(recipe):
    name, level, category, duration, ingredients, steps = recipe
    base = 3.5 + len(ingredients) * 0.65
    if level == 'Средне':
        base += 1.5
    elif level == 'Необычно':
        base += 2.5
    expensive = ('лосось', 'кревет', 'маскарпоне', 'авокадо', 'пармезан', 'моцарелла', 'говядин', 'свини', 'индейк', 'фета')
    base += sum(1.4 for i in ingredients if any(k in i.lower() for k in expensive))
    low, high = max(2, round(base - 1)), max(4, round(base + 2.5))
    return f"€{low}–€{high}"



@app.route("/")
def index():
    return render_template("index.html", movies=MOVIES, games=GAMES)

@app.route("/movies")
def movies():
    q = request.args.get("q", "").strip().lower()
    items = MOVIES if not q else [m for m in MOVIES if q in f"{m['title']} {m['genre']} {m['year']}".lower()]
    return render_template("movies.html", movies=items)

@app.route("/games")
def games():
    return render_template("games.html", games=GAMES)

@app.route("/bored")
def bored():
    return render_template("bored.html", activities=ACTIVITIES)

@app.route("/places")
def places():
    return render_template("places.html")

@app.route("/social")
def social():
    return render_template("social.html")

@app.route("/support")
def support():
    return render_template("support.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/privacy")
def privacy():
    return render_template("privacy.html")

@app.route("/policy")
def policy():
    return render_template("policy.html")

@app.route("/challenges")
def challenges():
    category = request.args.get("category", "all")
    if category != "all" and category not in CHALLENGE_CATEGORIES:
        category = "all"
    items = [c for c in CHALLENGES if category == "all" or c[2] == category]
    return render_template("challenges.html", challenges=items, category=category)

@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    con = sqlite3.connect(USER_DB)
    con.row_factory = sqlite3.Row
    user = con.execute("SELECT id, name, email, age FROM users WHERE id=?", (session["user_id"],)).fetchone()
    con.close()
    if not user:
        session.clear()
        return redirect(url_for("login"))
    return render_template("profile.html", user=user)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        password2 = request.form.get("password2", "")
        try:
            age = int(request.form.get("age", "0"))
        except ValueError:
            age = 0

        if not name or not re.fullmatch(r"[^@\\s]+@[^@\\s]+\\.[^@\\s]+", email) or len(password) < 8 or password != password2 or age < 16:
            flash("Проверьте данные: возраст должен быть 16+, email должен быть корректным, пароль — минимум 8 символов.", "error")
            return render_template("register.html")
        if not request.form.get("privacy"):
            flash("Нужно согласиться с политикой конфиденциальности.", "error")
            return render_template("register.html")

        try:
            con = sqlite3.connect(USER_DB)
            con.execute(
                "INSERT INTO users(name,email,password_hash,age,created_at,email_verified) VALUES(?,?,?,?,?,0)",
                (name, email, generate_password_hash(password), age, int(time.time()))
            )
            con.commit()
            user_id = con.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()[0]
            con.close()
            code = create_verification_code(user_id)
            try:
                send_verification_email(email, code)
            except Exception:
                con = sqlite3.connect(USER_DB)
                con.execute("DELETE FROM email_verifications WHERE user_id=?", (user_id,))
                con.execute("DELETE FROM users WHERE id=?", (user_id,))
                con.commit()
                con.close()
                flash("Не удалось отправить код подтверждения. Проверьте SMTP-настройки LIVO.", "error")
                return render_template("register.html")
        except sqlite3.IntegrityError:
            flash("Этот email уже зарегистрирован.", "error")
            return render_template("register.html")

        session["pending_verification_user_id"] = user_id
        session["verification_sent_at"] = time.time()
        flash("Код подтверждения отправлен на вашу почту.", "success")
        return redirect(url_for("verify_email"))
    return render_template("register.html")


@app.route("/verify-email", methods=["GET", "POST"])
def verify_email():
    user_id = session.get("pending_verification_user_id")
    if not user_id:
        return redirect(url_for("login"))

    con = sqlite3.connect(USER_DB)
    con.row_factory = sqlite3.Row
    user = con.execute("SELECT id,name,email,email_verified FROM users WHERE id=?", (user_id,)).fetchone()
    con.close()
    if not user:
        session.pop("pending_verification_user_id", None)
        return redirect(url_for("register"))
    if user["email_verified"]:
        session.pop("pending_verification_user_id", None)
        return redirect(url_for("login"))

    if request.method == "POST":
        code = re.sub(r"\\D", "", request.form.get("code", ""))[:6]
        con = sqlite3.connect(USER_DB)
        con.row_factory = sqlite3.Row
        row = con.execute("SELECT * FROM email_verifications WHERE user_id=? ORDER BY id DESC LIMIT 1", (user_id,)).fetchone()
        if not row:
            con.close()
            flash("Код не найден. Запросите новый код.", "error")
            return render_template("verify_email.html", email=user["email"])
        if row["attempts"] >= 5:
            con.close()
            flash("Слишком много попыток. Запросите новый код.", "error")
            return render_template("verify_email.html", email=user["email"])
        if int(time.time()) > row["expires_at"]:
            con.close()
            flash("Код истёк. Запросите новый код.", "error")
            return render_template("verify_email.html", email=user["email"])

        if len(code) != 6 or not check_password_hash(row["code_hash"], code):
            con.execute("UPDATE email_verifications SET attempts=attempts+1 WHERE id=?", (row["id"],))
            con.commit()
            con.close()
            flash("Неверный код подтверждения.", "error")
            return render_template("verify_email.html", email=user["email"])

        con.execute("UPDATE users SET email_verified=1 WHERE id=?", (user_id,))
        con.execute("DELETE FROM email_verifications WHERE user_id=?", (user_id,))
        con.commit()
        con.close()
        session.pop("pending_verification_user_id", None)
        session["user_id"] = user_id
        flash("Email подтверждён. Добро пожаловать в LIVO!", "success")
        return redirect(url_for("profile"))

    return render_template("verify_email.html", email=user["email"])


@app.route("/resend-verification", methods=["POST"])
def resend_verification():
    user_id = session.get("pending_verification_user_id")
    if not user_id:
        return redirect(url_for("login"))
    con = sqlite3.connect(USER_DB)
    con.row_factory = sqlite3.Row
    user = con.execute("SELECT id,email,email_verified FROM users WHERE id=?", (user_id,)).fetchone()
    con.close()
    if not user:
        session.pop("pending_verification_user_id", None)
        return redirect(url_for("register"))
    if user["email_verified"]:
        return redirect(url_for("login"))

    last_sent = session.get("verification_sent_at", 0)
    if time.time() - last_sent < 60:
        flash("Подождите немного перед повторной отправкой.", "error")
        return redirect(url_for("verify_email"))
    try:
        code = create_verification_code(user_id)
        send_verification_email(user["email"], code)
        session["verification_sent_at"] = time.time()
        flash("Новый код отправлен.", "success")
    except Exception:
        flash("Не удалось отправить письмо. Проверьте SMTP-настройки LIVO.", "error")
    return redirect(url_for("verify_email"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        con = sqlite3.connect(USER_DB)
        con.row_factory = sqlite3.Row
        user = con.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        con.close()
        if user and check_password_hash(user["password_hash"], password):
            if not user["email_verified"]:
                session["pending_verification_user_id"] = user["id"]
                try:
                    code = create_verification_code(user["id"])
                    send_verification_email(user["email"], code)
                    session["verification_sent_at"] = time.time()
                    flash("Сначала подтвердите email. Новый код отправлен.", "error")
                except Exception:
                    flash("Email ещё не подтверждён. Не удалось отправить новый код.", "error")
                return redirect(url_for("verify_email"))
            session["user_id"] = user["id"]
            return redirect(url_for("profile"))
        flash("Неверный email или пароль.", "error")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/pc-builder")
def pc_builder():
    parts = {
        "cpu": ["AMD Ryzen 5 7600", "AMD Ryzen 7 7800X3D", "Intel Core i5-14600K", "Intel Core i7-14700K"],
        "gpu": ["NVIDIA GeForce RTX 4060 8GB", "NVIDIA GeForce RTX 4070 12GB", "NVIDIA GeForce RTX 4080 16GB", "NVIDIA GeForce RTX 4090 24GB"],
        "ram": ["16 GB DDR5", "32 GB DDR5", "64 GB DDR5"],
        "storage": ["1 TB NVMe SSD", "2 TB NVMe SSD", "4 TB NVMe SSD"],
        "psu": ["650 W 80+ Gold", "750 W 80+ Gold", "850 W 80+ Gold", "1000 W 80+ Gold"],
        "cooler": ["Башенный кулер", "Dual-tower кулер", "240 мм СЖО"],
        "motherboard": ["B650", "B650E", "Z790", "X670"],
        "case": ["Mid Tower", "Airflow Mid Tower", "Full Tower"],
    }
    gpu = request.args.get("gpu", "RTX 4070 12GB")
    resolution = request.args.get("resolution", "1080p")
    fps_base = {"RTX 4060 8GB": 75, "RTX 4070 12GB": 110, "RTX 4080 16GB": 145, "RTX 4090 24GB": 175}
    base = fps_base.get(gpu, 110)
    divisor = {"1080p": 1, "1440p": 1.35, "4K": 2.0}.get(resolution, 1.35)
    games_fps = {"Cyberpunk 2077": round(base/divisor), "Elden Ring": round(base*0.82/divisor), "GTA V": round(base*1.2/divisor), "Minecraft": round(base*1.5/divisor)}
    return render_template("pc_builder.html", parts=parts, gpu=gpu, resolution=resolution, games=games_fps)

@app.route("/fitness")
def fitness():
    goal = request.args.get("goal", "fitness")
    level = request.args.get("level", "beginner")
    if goal not in FITNESS_GOALS:
        goal = "fitness"
    if level not in FITNESS_LEVELS:
        level = "beginner"
    selected_muscles = request.args.getlist("muscle")
    selected_equipment = request.args.getlist("equipment")
    exercises = _fitness_exercises(goal, level, selected_muscles, selected_equipment)
    plans = [p for p in WORKOUT_PLANS if level == p[1] and goal in p[2]]
    return render_template(
        "fitness.html",
        exercises=exercises,
        result_count=len(exercises),
        muscles=FITNESS_MUSCLES,
        equipment=FITNESS_EQUIPMENT,
        selected_muscles=selected_muscles,
        selected_equipment=selected_equipment,
        goal=goal,
        level=level,
        goals=FITNESS_GOALS,
        levels=FITNESS_LEVELS,
        workouts=plans,
    )


@app.route("/recipes")
def recipes():
    category = request.args.get("category", "all")
    level = request.args.get("level", "all")
    items = RECIPES
    if category != "all":
        items = [r for r in items if r[2] == category]
    if level != "all":
        items = [r for r in items if r[1] == level]
    detailed = [{
        "title": r[0], "level": r[1], "category": r[2], "time": r[3],
        "ingredients": r[4], "steps": r[5], "servings": 2, "cost": _recipe_cost(r)
    } for r in items]
    return render_template("recipes.html", recipes=detailed, category=category, level=level)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
