from pathlib import Path
import re
import functools, hmac, os, secrets, time
from flask import (Flask, Response, abort, flash, g, jsonify, redirect, render_template, send_file,
                   request, session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash
import userdb

app = Flask(__name__)
app.config.update(
    SECRET_KEY=userdb.secret_key(),
    MAX_CONTENT_LENGTH=3 * 1024 * 1024,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=bool(os.getenv("RENDER") or os.getenv("LIVO_HTTPS")),
    PERMANENT_SESSION_LIFETIME=60 * 60 * 24 * 30,
    JSON_AS_ASCII=False,
)
if os.getenv("RENDER"):
    from werkzeug.middleware.proxy_fix import ProxyFix
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)
userdb.init_db()


def csrf_token():
    token = session.get("_csrf")
    if not token:
        token = session["_csrf"] = secrets.token_urlsafe(32)
    return token


@app.before_request
def load_user_and_check_csrf():
    g.user = None
    if request.endpoint == "static":
        return
    uid = session.get("uid")
    if uid:
        g.user = userdb.get_user(uid)
        if g.user is None:
            session.pop("uid", None)
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        sent = request.headers.get("X-CSRF-Token") or request.form.get("csrf_token", "")
        if not sent or not hmac.compare_digest(sent.encode(), session.get("_csrf", "").encode()):
            if request.path.startswith("/api/"):
                return jsonify(error="Сессия устарела. Обнови страницу."), 400
            flash("Сессия устарела, попробуй ещё раз.", "error")
            return redirect(url_for("index"))


@app.context_processor
def inject_globals():
    return {"user": g.get("user"), "csrf_token": csrf_token,
            "in_app": "LIVOApp" in request.headers.get("User-Agent", "")}


@app.after_request
def security_headers(resp):
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    resp.headers.setdefault("Referrer-Policy", "same-origin")
    return resp


@app.template_filter("datefmt")
def datefmt(ts):
    return time.strftime("%d.%m.%Y %H:%M", time.gmtime(ts))


@app.template_filter("hue")
def hue(title):
    h = 0
    for ch in str(title):
        h = (h * 31 + ord(ch)) % 360
    return h


@app.template_filter("initial")
def initial(name):
    return (name or "?").strip()[:1].upper() or "?"


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
    {"title": 'Zodiac', "genre": 'Триллер / Криминал', "year": 2007, "rating": "—"},
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

from movies_extra import MOVIES_EXTRA
_seen = {(m["title"].lower(), m["year"]) for m in MOVIES}
MOVIES.extend(m for m in MOVIES_EXTRA if (m["title"].lower(), m["year"]) not in _seen)

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


import os, sqlite3, time, requests
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

FITNESS_EXERCISES = [('Жим лёжа со штангой', 'Грудь', 'Штанга + скамья', '3–4', '8–12'), ('Жим гантелей лёжа', 'Грудь', 'Гантели + скамья', '3–4', '8–12'), ('Жим гантелей на наклонной скамье', 'Верх груди', 'Гантели + наклонная скамья', '3', '8–12'), ('Разводка с гантелями', 'Грудь', 'Гантели + скамья', '3', '10–15'), ('Сведение рук в тренажёре', 'Грудь', 'Пек-дек', '3', '10–15'), ('Отжимания', 'Грудь / трицепс', 'Собственный вес', '3', '8–20'), ('Подтягивания', 'Спина / бицепс', 'Турник', '3–4', '5–12'), ('Тяга верхнего блока', 'Спина', 'Блочный тренажёр', '3–4', '8–12'), ('Тяга горизонтального блока', 'Спина', 'Блочный тренажёр', '3–4', '8–12'), ('Тяга штанги в наклоне', 'Спина', 'Штанга', '3–4', '6–12'), ('Тяга гантели одной рукой', 'Спина', 'Гантель + скамья', '3', '8–12'), ('Гиперэкстензия', 'Поясница / ягодицы', 'Гиперэкстензия', '3', '10–15'), ('Жим ногами', 'Ноги', 'Тренажёр для жима ногами', '3–4', '8–15'), ('Приседания со штангой', 'Ноги / ягодицы', 'Штанга + стойка', '3–4', '6–12'), ('Гакк-присед', 'Ноги', 'Гакк-машина', '3', '8–12'), ('Разгибание ног', 'Квадрицепс', 'Тренажёр разгибания ног', '3', '10–15'), ('Сгибание ног лёжа', 'Бицепс бедра', 'Тренажёр сгибания ног', '3', '10–15'), ('Румынская тяга', 'Задняя поверхность бедра', 'Штанга', '3', '8–12'), ('Выпады с гантелями', 'Ноги / ягодицы', 'Гантели', '3', '8–12 на ногу'), ('Ягодичный мост', 'Ягодицы', 'Штанга / тренажёр', '3–4', '8–15'), ('Подъём на носки стоя', 'Икры', 'Тренажёр / гантели', '3–4', '12–20'), ('Жим гантелей сидя', 'Плечи', 'Гантели + скамья', '3', '8–12'), ('Жим штанги над головой', 'Плечи', 'Штанга', '3', '6–10'), ('Разведения гантелей в стороны', 'Средняя дельта', 'Гантели', '3', '10–15'), ('Обратная бабочка', 'Задняя дельта', 'Тренажёр', '3', '10–15'), ('Тяга каната к лицу', 'Плечи / верх спины', 'Кроссовер', '3', '10–15'), ('Подъём штанги на бицепс', 'Бицепс', 'Штанга', '3', '8–12'), ('Сгибание рук с гантелями', 'Бицепс', 'Гантели', '3', '8–12'), ('Молотковые сгибания', 'Бицепс', 'Гантели', '3', '8–12'), ('Разгибание рук на блоке', 'Трицепс', 'Кроссовер', '3', '10–15'), ('Французский жим', 'Трицепс', 'EZ-штанга / гантель', '3', '8–12'), ('Разгибание руки с гантелью из-за головы', 'Трицепс', 'Гантель', '3', '10–15'), ('Скручивания', 'Пресс', 'Скамья / коврик', '3', '12–20'), ('Подъём коленей в упоре', 'Пресс', 'Турник / брусья', '3', '10–15'), ('Подъём ног в висе', 'Пресс', 'Турник', '3', '8–15'), ('Планка', 'Кор', 'Собственный вес', '3', '30–60 сек'), ('Ролик для пресса', 'Кор', 'Аб-роллер', '3', '6–15'), ('Бёрпи', 'Кардио / всё тело', 'Собственный вес', '3', '8–15'), ('Прыжки на тумбу', 'Ноги / кардио', 'Плио-тумба', '3', '6–12'), ('Канаты', 'Кардио / всё тело', 'Battle ropes', '6', '20–30 сек'), ('Гребля', 'Кардио / всё тело', 'Гребной тренажёр', '1', '10–20 мин'), ('Беговая дорожка', 'Кардио', 'Беговая дорожка', '1', '15–30 мин'), ('Велотренажёр', 'Кардио', 'Велотренажёр', '1', '15–30 мин'), ('Эллиптический тренажёр', 'Кардио', 'Эллипсоид', '1', '15–30 мин'), ('Степпер', 'Кардио', 'Степпер', '1', '10–20 мин')]

PC_PARTS = {'cpu': ['AMD Ryzen 5 5600', 'AMD Ryzen 5 7600', 'AMD Ryzen 5 9600X', 'AMD Ryzen 7 7800X3D', 'AMD Ryzen 7 9800X3D', 'Intel Core i5-14400F', 'Intel Core i5-14600K', 'Intel Core i7-14700K', 'Intel Core Ultra 7 265K'], 'gpu': ['NVIDIA GeForce RTX 4060 8GB', 'NVIDIA GeForce RTX 4060 Ti 8GB', 'NVIDIA GeForce RTX 4070 SUPER 12GB', 'NVIDIA GeForce RTX 4070 Ti SUPER 16GB', 'NVIDIA GeForce RTX 5070 12GB', 'NVIDIA GeForce RTX 5070 Ti 16GB', 'NVIDIA GeForce RTX 5080 16GB', 'AMD Radeon RX 7600 8GB', 'AMD Radeon RX 7800 XT 16GB', 'AMD Radeon RX 7900 XTX 24GB'], 'ram': ['16GB DDR4', '32GB DDR4', '16GB DDR5', '32GB DDR5', '64GB DDR5'], 'storage': ['1TB NVMe SSD', '2TB NVMe SSD', '1TB SATA SSD + 2TB NVMe SSD', '2TB NVMe SSD + 4TB HDD'], 'psu': ['550W 80+ Bronze', '650W 80+ Gold', '750W 80+ Gold', '850W 80+ Gold', '1000W 80+ Gold'], 'cooler': ['Boxed/Air cooler', 'Tower air cooler', '240mm AIO', '360mm AIO'], 'motherboard': ['B550', 'B650', 'B850', 'Z790', 'B760', 'Z890'], 'case': ['Mid Tower Airflow', 'Mid Tower RGB', 'Full Tower', 'Compact ATX']}
FPS_PROFILES = {'RTX 4060': {'1080p': {'Fortnite': 173, 'CS2': 317, 'Valorant': 465, 'Cyberpunk 2077': 77, 'GTA V': 149, 'Warzone': 110, 'Red Dead Redemption 2': 78, 'Minecraft': 365}, '1440p': {'Fortnite': 110, 'CS2': 210, 'Valorant': 397, 'Cyberpunk 2077': 58, 'GTA V': 101, 'Warzone': 75, 'Red Dead Redemption 2': 55, 'Minecraft': 231}, '4K': {'Fortnite': 58, 'CS2': 117, 'Valorant': 317, 'Cyberpunk 2077': 38, 'GTA V': 58, 'Warzone': 44, 'Red Dead Redemption 2': 31, 'Minecraft': 121}}, 'RTX 4070 SUPER': {'1080p': {'Fortnite': 265, 'CS2': 487, 'Valorant': 487, 'Cyberpunk 2077': 109, 'GTA V': 229, 'Warzone': 177, 'Red Dead Redemption 2': 126, 'Minecraft': 561}, '1440p': {'Fortnite': 168, 'CS2': 323, 'Valorant': 462, 'Cyberpunk 2077': 89, 'GTA V': 155, 'Warzone': 158, 'Red Dead Redemption 2': 94, 'Minecraft': 354}, '4K': {'Fortnite': 89, 'CS2': 180, 'Valorant': 429, 'Cyberpunk 2077': 59, 'GTA V': 89, 'Warzone': 133, 'Red Dead Redemption 2': 62, 'Minecraft': 185}}, 'RTX 5070': {'1080p': {'Fortnite': 290, 'CS2': 500, 'Valorant': 600, 'Cyberpunk 2077': 125, 'GTA V': 240, 'Warzone': 190, 'Red Dead Redemption 2': 135, 'Minecraft': 600}, '1440p': {'Fortnite': 210, 'CS2': 390, 'Valorant': 540, 'Cyberpunk 2077': 95, 'GTA V': 175, 'Warzone': 160, 'Red Dead Redemption 2': 105, 'Minecraft': 450}, '4K': {'Fortnite': 120, 'CS2': 220, 'Valorant': 390, 'Cyberpunk 2077': 65, 'GTA V': 95, 'Warzone': 105, 'Red Dead Redemption 2': 70, 'Minecraft': 230}}, 'RTX 5070 Ti': {'1080p': {'Fortnite': 320, 'CS2': 550, 'Valorant': 650, 'Cyberpunk 2077': 145, 'GTA V': 260, 'Warzone': 220, 'Red Dead Redemption 2': 155, 'Minecraft': 650}, '1440p': {'Fortnite': 240, 'CS2': 430, 'Valorant': 570, 'Cyberpunk 2077': 115, 'GTA V': 195, 'Warzone': 190, 'Red Dead Redemption 2': 125, 'Minecraft': 500}, '4K': {'Fortnite': 150, 'CS2': 250, 'Valorant': 430, 'Cyberpunk 2077': 80, 'GTA V': 110, 'Warzone': 125, 'Red Dead Redemption 2': 82, 'Minecraft': 270}}}

RECIPES = [('Омлет с сыром', 'Очень просто', 'Завтрак', '10 мин', ['2 яйца', '30 г сыра', '1 ч. л. масла', 'соль'], ['Взбей яйца с солью.', 'Разогрей сковороду с маслом.', 'Влей яйца, посыпь сыром и готовь 3–5 минут.']), ('Горячие бутерброды', 'Очень просто', 'Завтрак', '10 мин', ['4 ломтика хлеба', 'сыр', 'помидор', 'ветчина по желанию'], ['Собери бутерброды.', 'Запекай при 180°C около 7–10 минут.', 'Подавай горячими.']), ('Паста с чесноком', 'Очень просто', 'Обед', '15 мин', ['200 г пасты', '2 зубчика чеснока', '2 ст. л. масла', 'сыр'], ['Отвари пасту.', 'Обжарь чеснок в масле 1–2 минуты.', 'Смешай с пастой и сыром.']), ('Картофель по-деревенски', 'Просто', 'Гарнир', '40 мин', ['500 г картофеля', '1 ст. л. масла', 'паприка', 'соль'], ['Нарежь картофель дольками.', 'Перемешай со специями и маслом.', 'Запекай при 200°C 30–35 минут.']), ('Кесадилья с сыром', 'Просто', 'Перекус', '15 мин', ['2 тортильи', '100 г сыра', 'кукуруза', 'помидор'], ['Разложи начинку на тортилье.', 'Накрой второй и обжарь на сухой сковороде.', 'Нарежь треугольниками.']), ('Домашняя пицца', 'Просто', 'Ужин', '45 мин', ['тесто', 'томатный соус', 'сыр', 'помидоры', 'грибы'], ['Раскатай тесто.', 'Добавь соус и начинку.', 'Выпекай при 220°C 12–15 минут.']), ('Курица терияки', 'Средне', 'Ужин', '30 мин', ['500 г курицы', 'соевый соус', 'мёд', 'чеснок', 'рис'], ['Нарежь курицу и обжарь.', 'Добавь соевый соус, мёд и чеснок.', 'Подавай с рисом.']), ('Рамен дома', 'Средне', 'Ужин', '30 мин', ['лапша', 'бульон', 'яйцо', 'грибы', 'зелёный лук'], ['Приготовь бульон.', 'Добавь лапшу и грибы.', 'Подавай с варёным яйцом и зелёным луком.']), ('Шакшука', 'Средне', 'Завтрак', '25 мин', ['4 яйца', '400 г томатов', 'лук', 'перец', 'паприка'], ['Обжарь лук и перец.', 'Добавь томаты и специи.', 'Сделай углубления, разбей яйца и накрой крышкой.']), ('Тыквенный крем-суп', 'Средне', 'Суп', '40 мин', ['500 г тыквы', 'лук', '500 мл бульона', 'сливки'], ['Запеки или потуши тыкву с луком.', 'Добавь бульон и провари.', 'Измельчи блендером и добавь сливки.']), ('Лазанья', 'Средне', 'Ужин', '90 мин', ['листы лазаньи', 'фарш', 'томатный соус', 'сыр', 'бешамель'], ['Приготовь мясной соус.', 'Выкладывай слоями пасту, соус и сыр.', 'Запекай при 180°C около 40 минут.']), ('Домашние суши-роллы', 'Средне', 'Ужин', '60 мин', ['рис для суши', 'нори', 'огурец', 'авокадо', 'лосось или креветка'], ['Приготовь рис.', 'Разложи рис на нори и добавь начинку.', 'Сверни ролл и нарежь.']), ('Гёдза', 'Необычно', 'Ужин', '60 мин', ['тесто для гёдза', 'фарш', 'капуста', 'имбирь', 'соевый соус'], ['Смешай начинку.', 'Сформируй небольшие пельмени.', 'Обжарь дно, добавь немного воды и накрой крышкой.']), ('Корейский корн-дог', 'Необычно', 'Перекус', '40 мин', ['сосиски', 'моцарелла', 'мука', 'молоко', 'панировочные сухари'], ['Насади сосиску и сыр на шпажку.', 'Окуни в густое тесто и сухари.', 'Обжарь до золотистой корочки.']), ('Домашний поке', 'Необычно', 'Обед', '25 мин', ['рис', 'лосось или тофу', 'авокадо', 'огурец', 'кунжут'], ['Приготовь рис.', 'Нарежь ингредиенты.', 'Собери всё в миске и добавь соус.']), ('Тако с хрустящей курицей', 'Необычно', 'Ужин', '45 мин', ['тортильи', 'курица', 'панировка', 'салат', 'томатный соус'], ['Запанируй и приготовь курицу.', 'Прогрей тортильи.', 'Собери тако с овощами и соусом.']), ('Паста в съедобной сырной корзинке', 'Необычно', 'Ужин', '35 мин', ['паста', 'твёрдый сыр', 'сливочный соус', 'грибы'], ['Растопи сыр на сковороде и сформируй корзинку.', 'Приготовь пасту и соус.', 'Положи пасту в сырную корзинку.']), ('Радужные панкейки', 'Необычно', 'Завтрак', '30 мин', ['мука', 'молоко', 'яйца', 'разрыхлитель', 'пищевые красители'], ['Сделай тесто и раздели на части.', 'Добавь немного пищевого красителя.', 'Испеки маленькие панкейки и сложи стопкой.']), ('Шоколадная лава-кейк', 'Необычно', 'Десерт', '25 мин', ['100 г шоколада', '50 г масла', '2 яйца', '50 г сахара', '30 г муки'], ['Растопи шоколад с маслом.', 'Смешай с яйцами, сахаром и мукой.', 'Запекай при 200°C примерно 8–10 минут.']), ('Мороженое из банана', 'Очень просто', 'Десерт', '10 мин + заморозка', ['2 банана', 'какао или ягоды'], ['Заморозь нарезанные бананы.', 'Пробей блендером до кремовой текстуры.', 'Добавь какао или ягоды.']), ('Тирамису в стакане', 'Средне', 'Десерт', '30 мин', ['печенье савоярди', 'маскарпоне', 'кофе', 'какао'], ['Сделай крем из маскарпоне.', 'Обмакни печенье в кофе.', 'Выложи слоями и охлади.']), ('Японский чизкейк', 'Необычно', 'Десерт', '90 мин', ['сливочный сыр', 'яйца', 'молоко', 'мука', 'сахар'], ['Приготовь нежное тесто.', 'Перелей в форму.', 'Выпекай на водяной бане при умеренной температуре.']), ('Домашняя лапша с арахисовым соусом', 'Необычно', 'Обед', '25 мин', ['лапша', 'арахисовая паста', 'соевый соус', 'лайм', 'чеснок'], ['Отвари лапшу.', 'Смешай ингредиенты соуса.', 'Перемешай лапшу с соусом и добавь кунжут.']), ('Хрустящий нут', 'Просто', 'Перекус', '35 мин', ['консервированный нут', 'масло', 'паприка', 'соль'], ['Промой и хорошо обсуши нут.', 'Смешай со специями и маслом.', 'Запекай при 200°C 25–30 минут.']), ('Яблочный крамбл', 'Просто', 'Десерт', '40 мин', ['яблоки', 'овсяные хлопья', 'мука', 'масло', 'сахар'], ['Нарежь яблоки.', 'Смешай крошку из хлопьев, муки и масла.', 'Запекай при 180°C около 25 минут.'])]

# ---------------------------------------------------------------------------
# ID для карточек + публичные страницы
# ---------------------------------------------------------------------------
for _i, _m in enumerate(MOVIES):
    _m["id"] = _i
for _i, _g in enumerate(GAMES):
    _g["id"] = _i

KINDS = {"movie": MOVIES, "game": GAMES}
# id фильма = позиция в MOVIES (не менять порядок, только дописывать в конец!),
# а в каталоге показываем от новых к старым.
MOVIES_BY_YEAR = sorted(MOVIES, key=lambda m: (-m["year"], m["id"]))
_HOME_PICKS = ["Inception", "Interstellar", "Dune: Part Two", "Oppenheimer", "The Dark Knight",
               "Parasite", "Spider-Man: Across the Spider-Verse", "Mad Max: Fury Road"]
HOME_MOVIES = [m for t in _HOME_PICKS for m in MOVIES if m["title"] == t][:8]


@app.route("/")
def index():
    return render_template("index.html", movies=HOME_MOVIES)


@app.route("/movies")
def movies():
    return render_template("movies.html", total=len(MOVIES), q=request.args.get("q", "").strip()[:80])


@app.route("/movies/<int:movie_id>")
def movie_detail(movie_id):
    if not 0 <= movie_id < len(MOVIES):
        abort(404)
    movie = MOVIES[movie_id]
    if g.user:
        userdb.add_history(g.user["id"], movie_id)
    tokens = {t.strip() for t in movie["genre"].split("/")}
    related = [m for m in MOVIES if m["id"] != movie_id and tokens & {t.strip() for t in m["genre"].split("/")}]
    related.sort(key=lambda m: abs(m["year"] - movie["year"]))
    is_fav = bool(g.user) and movie_id in userdb.favorite_ids(g.user["id"], "movie")
    return render_template("movie.html", movie=movie, related=related[:6], is_fav=is_fav)


@app.route("/games")
def games():
    return render_template("games.html", total=len(GAMES), q=request.args.get("q", "").strip()[:80])


@app.route("/bored")
def bored():
    return render_template("bored.html", activities=ACTIVITIES)


# ---------------------------------------------------------------------------
# JSON API: живой поиск без перезагрузки
# ---------------------------------------------------------------------------
def _match(q, *parts):
    hay = " ".join(str(p) for p in parts).lower()
    return all(word in hay for word in q.lower().split())


def _limit():
    try:
        return max(1, min(int(request.args.get("limit", 500)), 500))
    except ValueError:
        return 500


@app.get("/api/movies")
def api_movies():
    q = request.args.get("q", "")[:80]
    favs = set(userdb.favorite_ids(g.user["id"], "movie")) if g.user else set()
    out = [
        {"id": m["id"], "title": m["title"], "genre": m["genre"], "year": m["year"],
         "rating": m["rating"], "fav": m["id"] in favs}
        for m in MOVIES_BY_YEAR if _match(q, m["title"], m["genre"], m["year"])
    ]
    return jsonify(total=len(out), items=out[:_limit()])


@app.get("/api/games")
def api_games():
    q = request.args.get("q", "")[:80]
    genre = request.args.get("genre", "all").lower()
    favs = set(userdb.favorite_ids(g.user["id"], "game")) if g.user else set()
    out = [
        {"id": x["id"], "title": x["title"], "genre": x["genre"], "year": x["year"],
         "platform": x["platform"], "fav": x["id"] in favs}
        for x in GAMES
        if _match(q, x["title"], x["genre"], x["platform"], x["year"])
        and (genre == "all" or genre in x["genre"].lower())
    ]
    return jsonify(total=len(out), items=out[:_limit()])


# ---------------------------------------------------------------------------
# Постеры: TMDB (официальные постеры, поиск по названию и году) + запасной вариант Wikipedia.
# Ключ TMDB берётся из переменной окружения TMDB_API_KEY (бесплатно на themoviedb.org).
# Если постер не найден, показывается заглушка — чужие картинки не подставляются.
# ---------------------------------------------------------------------------
_POSTER_MEM = {}          # (kind, title, year) -> (url, saved_at)
_POSTER_OK_TTL = 60 * 60 * 24 * 30
_POSTER_FAIL_TTL = 60 * 10
_UA = {"User-Agent": "LIVO/1.0 (https://livo.onrender.com; poster lookup)"}


def _norm_title(t):
    t = re.sub(r"\(.*?\)", "", str(t).lower())
    return re.sub(r"[^a-z0-9а-яё]+", "", t)


def _poster_db():
    con = sqlite3.connect(str(userdb.DATA_DIR / "livo_posters.db"), timeout=10)
    con.execute("CREATE TABLE IF NOT EXISTS posters(k TEXT PRIMARY KEY, url TEXT NOT NULL, saved_at INTEGER NOT NULL)")
    return con


def _poster_db_get(key):
    try:
        with _poster_db() as con:
            row = con.execute("SELECT url, saved_at FROM posters WHERE k=?", (key,)).fetchone()
        if row and time.time() - row[1] < _POSTER_OK_TTL:
            return row[0]
    except Exception:
        pass
    return ""


def _poster_db_set(key, url):
    try:
        with _poster_db() as con:
            con.execute("INSERT OR REPLACE INTO posters(k,url,saved_at) VALUES(?,?,?)", (key, url, int(time.time())))
    except Exception:
        pass


def _tmdb_request(path, params):
    key = os.getenv("TMDB_API_KEY", "").strip()
    if not key:
        return None
    headers = dict(_UA)
    params = dict(params, include_adult="false", language="en-US")
    if key.startswith("eyJ"):                       # токен v4 (Bearer)
        headers["Authorization"] = f"Bearer {key}"
    else:                                           # ключ v3
        params["api_key"] = key
    r = requests.get(f"https://api.themoviedb.org/3{path}", params=params, headers=headers, timeout=6)
    r.raise_for_status()
    return r.json().get("results", [])


def _pick_tmdb(results, title, year):
    """Выбирает результат с постером: сначала совпадение названия И года (±1), потом точное название."""
    want = _norm_title(title)
    cands = []
    for r in results or []:
        if not r.get("poster_path"):
            continue
        names = {_norm_title(r.get("title") or r.get("name") or ""),
                 _norm_title(r.get("original_title") or r.get("original_name") or "")}
        date = (r.get("release_date") or r.get("first_air_date") or "")[:4]
        year_ok = bool(year and date.isdigit() and abs(int(date) - int(year)) <= 1)
        cands.append((want in names, year_ok, r.get("popularity", 0), r["poster_path"]))
    for need_year in (True, False):
        pool = [c for c in cands if c[0] and (c[1] or not need_year)]
        if pool:
            return "https://image.tmdb.org/t/p/w500" + max(pool, key=lambda c: c[2])[3]
    return ""


def _tmdb_poster(title, year):
    for path, ykey in (("/search/movie", "year"), ("/search/tv", "first_air_date_year")):
        for use_year in ((True, False) if year else (False,)):
            params = {"query": title}
            if use_year:
                params[ykey] = year
            try:
                results = _tmdb_request(path, params)
            except Exception:
                return ""
            if results is None:                      # ключ не задан
                return ""
            url = _pick_tmdb(results, title, year)
            if url:
                return url
    return ""


def _wiki_poster(title, year, kind):
    """Запасной вариант. Для фильмов принимаем только страницу с тем же названием и тем же годом."""
    if kind == "game":
        queries = [f"{title} video game {year}", f"{title} video game"]
        words = ("video game", "videogame", "game developed", "game published")
    else:
        queries = [f"{title} {year} film", f"{title} film"]
        words = ("film", "movie", "miniseries", "television series", "animated")
    want = _norm_title(title)
    for q in queries:
        try:
            r = requests.get(
                "https://en.wikipedia.org/w/api.php",
                params={"action": "query", "generator": "search", "gsrsearch": q, "gsrnamespace": 0,
                        "gsrlimit": 6, "prop": "pageimages|extracts", "piprop": "thumbnail",
                        "pithumbsize": 600, "exintro": 1, "explaintext": 1, "exsentences": 2,
                        "exlimit": "max", "format": "json"},
                headers=_UA, timeout=6)
            r.raise_for_status()
            pages = sorted((r.json().get("query") or {}).get("pages", {}).values(),
                           key=lambda p: p.get("index", 99))
        except Exception:
            continue
        for p in pages:
            thumb = (p.get("thumbnail") or {}).get("source")
            if not thumb:
                continue
            text = ((p.get("title") or "") + " " + (p.get("extract") or "")).lower()
            if not any(w in text for w in words):
                continue
            ptitle = _norm_title(p.get("title", ""))
            if not (want and (want == ptitle or want in ptitle)):
                continue
            if kind == "movie" and year and str(year) not in text:
                continue
            return thumb
    return ""


def find_poster(title, year, kind):
    if kind == "movie":
        url = _tmdb_poster(title, year)
        if url:
            return url
    return _wiki_poster(title, year, kind)


@app.get("/api/poster")
def api_poster():
    title = request.args.get("title", "").strip()[:120]
    kind = "game" if request.args.get("kind") == "game" else "movie"
    year = re.sub(r"\D", "", request.args.get("year", ""))[:4]
    if not title:
        return jsonify(url="")
    key = (kind, title.lower(), year)
    now = time.time()
    hit = _POSTER_MEM.get(key)
    if hit and now - hit[1] < (_POSTER_OK_TTL if hit[0] else _POSTER_FAIL_TTL):
        url = hit[0]
    else:
        dbkey = "|".join(key)
        url = _poster_db_get(dbkey) or find_poster(title, year, kind)
        if url:
            _poster_db_set(dbkey, url)
        if len(_POSTER_MEM) > 5000:
            _POSTER_MEM.clear()
        _POSTER_MEM[key] = (url, now)
    resp = jsonify(url=url)
    resp.headers["Cache-Control"] = "public, max-age=86400" if url else "no-store"
    return resp


@app.post("/api/favorite")
def api_favorite():
    if not g.user:
        return jsonify(error="Войди в аккаунт, чтобы добавлять в избранное.", login=True), 401
    data = request.get_json(silent=True) or {}
    kind, item_id = data.get("kind"), data.get("id")
    if kind not in KINDS or not isinstance(item_id, int) or not 0 <= item_id < len(KINDS[kind]):
        return jsonify(error="Неверный запрос."), 400
    state = userdb.toggle_favorite(g.user["id"], kind, item_id)
    return jsonify(favorited=state, title=KINDS[kind][item_id]["title"])


@app.post("/api/theme")
def api_theme():
    data = request.get_json(silent=True) or {}
    theme = data.get("theme")
    if theme not in ("light", "dark", "auto"):
        return jsonify(error="Неверная тема."), 400
    if g.user:
        userdb.set_theme(g.user["id"], theme)
    return jsonify(ok=True)


# ---------------------------------------------------------------------------
# Аккаунты: регистрация, вход, профиль
# ---------------------------------------------------------------------------
USERNAME_RE = re.compile(r"^[A-Za-z0-9_.\-А-Яа-яЁё]{3,24}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
DUMMY_HASH = generate_password_hash("livo-dummy-password")
_attempts = {}


def _rate_limited():
    now = time.time()
    ip = request.remote_addr or "?"
    recent = [t for t in _attempts.get(ip, []) if now - t < 600]
    _attempts[ip] = recent
    return len(recent) >= 8


def _note_failure():
    _attempts.setdefault(request.remote_addr or "?", []).append(time.time())


def safe_next(url, default):
    if url and url.startswith("/") and not url.startswith("//") and "\\" not in url:
        return url
    return default


def login_required(view):
    @functools.wraps(view)
    def wrapper(*args, **kwargs):
        if not g.user:
            flash("Сначала войди в аккаунт.", "info")
            return redirect(url_for("login", next=request.full_path.rstrip("?")))
        return view(*args, **kwargs)
    return wrapper


def validate_profile_fields(username, email, exclude_id=0):
    errors = {}
    if not USERNAME_RE.match(username):
        errors["username"] = "3–24 символа: буквы, цифры, точка, дефис, подчёркивание."
    elif userdb.exists("username", username, exclude_id):
        errors["username"] = "Это имя пользователя уже занято."
    if len(email) > 120 or not EMAIL_RE.match(email):
        errors["email"] = "Введи корректный email."
    elif userdb.exists("email", email, exclude_id):
        errors["email"] = "Этот email уже зарегистрирован."
    return errors


def start_session(uid):
    session.clear()
    session["uid"] = uid
    session.permanent = True


@app.route("/register", methods=["GET", "POST"])
def register():
    if g.user:
        return redirect(url_for("profile"))
    form, errors = {}, {}
    if request.method == "POST":
        form = {k: request.form.get(k, "").strip() for k in ("username", "email")}
        password = request.form.get("password", "")
        errors = validate_profile_fields(form["username"], form["email"])
        if not 8 <= len(password) <= 128:
            errors["password"] = "Пароль — от 8 до 128 символов."
        elif password != request.form.get("password2", ""):
            errors["password2"] = "Пароли не совпадают."
        if not errors:
            uid = userdb.create_user(form["email"], form["username"], generate_password_hash(password))
            start_session(uid)
            flash("Добро пожаловать в LIVO! 🎉", "success")
            return redirect(safe_next(request.args.get("next"), url_for("profile")))
    return render_template("register.html", form=form, errors=errors)


@app.route("/login", methods=["GET", "POST"])
def login():
    if g.user:
        return redirect(url_for("profile"))
    error, ident = None, ""
    if request.method == "POST":
        ident = request.form.get("login", "").strip()[:120]
        password = request.form.get("password", "")[:128]
        if _rate_limited():
            error = "Слишком много попыток. Подожди 10 минут."
        else:
            row = userdb.find_user(ident) if ident else None
            ok = check_password_hash(row["pw_hash"] if row else DUMMY_HASH, password)
            if row and ok:
                start_session(row["id"])
                flash("С возвращением! 👋", "success")
                return redirect(safe_next(request.args.get("next"), url_for("profile")))
            _note_failure()
            error = "Неверный логин или пароль."
    return render_template("login.html", error=error, ident=ident)


@app.post("/logout")
def logout():
    session.clear()
    flash("Ты вышел из аккаунта.", "info")
    return redirect(url_for("index"))


@app.route("/profile")
@login_required
def profile():
    tab = request.args.get("tab", "favorites")
    if tab not in ("favorites", "history", "settings"):
        tab = "favorites"
    uid = g.user["id"]
    fav_movies = [MOVIES[i] for i in userdb.favorite_ids(uid, "movie") if i < len(MOVIES)]
    fav_games = [GAMES[i] for i in userdb.favorite_ids(uid, "game") if i < len(GAMES)]
    history = [(MOVIES[i], ts) for i, ts in userdb.history_items(uid) if i < len(MOVIES)]
    return render_template("profile.html", tab=tab, fav_movies=fav_movies, fav_games=fav_games,
                           history=history, errors={})


@app.post("/profile/settings")
@login_required
def profile_settings():
    u = g.user
    display = request.form.get("display_name", "").strip()[:40] or u["username"]
    bio = request.form.get("bio", "").strip()[:200]
    username = request.form.get("username", "").strip()
    email = request.form.get("email", "").strip()
    theme = request.form.get("theme", "auto")
    errors = validate_profile_fields(username, email, u["id"])
    if theme not in ("light", "dark", "auto"):
        theme = "auto"
    if errors:
        for msg in errors.values():
            flash(msg, "error")
        return redirect(url_for("profile", tab="settings"))
    userdb.update_profile(u["id"], display, bio, username, email, show_stats=bool(request.form.get("show_stats")))
    userdb.set_theme(u["id"], theme)
    flash("Настройки сохранены ✅", "success")
    return redirect(url_for("profile", tab="settings"))


@app.post("/profile/password")
@login_required
def profile_password():
    new = request.form.get("new_password", "")
    if not check_password_hash(g.user["pw_hash"], request.form.get("current_password", "")):
        flash("Текущий пароль указан неверно.", "error")
    elif not 8 <= len(new) <= 128:
        flash("Новый пароль — от 8 до 128 символов.", "error")
    elif new != request.form.get("new_password2", ""):
        flash("Новые пароли не совпадают.", "error")
    else:
        userdb.set_password(g.user["id"], generate_password_hash(new))
        flash("Пароль изменён 🔒", "success")
    return redirect(url_for("profile", tab="settings"))


IMAGE_SIGNATURES = (
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"GIF87a", "image/gif"),
    (b"GIF89a", "image/gif"),
)
AVATAR_MAX = 2 * 1024 * 1024


def sniff_image(data):
    for sig, mime in IMAGE_SIGNATURES:
        if data.startswith(sig):
            return mime
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


@app.post("/profile/avatar")
@login_required
def profile_avatar():
    file = request.files.get("avatar")
    data = file.read(AVATAR_MAX + 1) if file else b""
    mime = sniff_image(data) if data else None
    if not data:
        flash("Выбери файл с изображением.", "error")
    elif len(data) > AVATAR_MAX:
        flash("Файл слишком большой (максимум 2 МБ).", "error")
    elif not mime:
        flash("Поддерживаются только PNG, JPG, WEBP и GIF.", "error")
    else:
        userdb.set_avatar(g.user["id"], data, mime)
        flash("Аватар обновлён 📸", "success")
    return redirect(url_for("profile", tab="settings"))


@app.post("/profile/avatar/delete")
@login_required
def profile_avatar_delete():
    userdb.set_avatar(g.user["id"], None, None)
    flash("Аватар удалён.", "info")
    return redirect(url_for("profile", tab="settings"))


@app.get("/avatar/<int:uid>")
def avatar(uid):
    row = userdb.get_avatar(uid)
    if not row or row["avatar"] is None:
        abort(404)
    resp = Response(row["avatar"], mimetype=row["avatar_mime"])
    resp.headers["Cache-Control"] = "public, max-age=31536000, immutable"
    return resp


@app.post("/profile/history/clear")
@login_required
def history_clear():
    userdb.clear_history(g.user["id"])
    flash("История просмотров очищена.", "info")
    return redirect(url_for("profile", tab="history"))


@app.post("/profile/delete")
@login_required
def profile_delete():
    if not check_password_hash(g.user["pw_hash"], request.form.get("password", "")):
        flash("Пароль неверный — аккаунт не удалён.", "error")
        return redirect(url_for("profile", tab="settings"))
    userdb.delete_user(g.user["id"])
    session.clear()
    flash("Аккаунт удалён. Будем скучать 💜", "info")
    return redirect(url_for("index"))


@app.errorhandler(413)
def too_large(_):
    flash("Файл слишком большой (максимум 2 МБ).", "error")
    return redirect(url_for("profile", tab="settings") if g.get("user") else url_for("index"))


@app.errorhandler(404)
def not_found(_):
    return render_template("404.html"), 404


# ---------------------------------------------------------------------------
# Друзья и публичные профили
# ---------------------------------------------------------------------------
_user_search_hits = {}


def _search_throttled():
    now = time.time()
    ip = request.remote_addr or "?"
    recent = [t for t in _user_search_hits.get(ip, []) if now - t < 60]
    recent.append(now)
    _user_search_hits[ip] = recent
    if len(_user_search_hits) > 2000:
        _user_search_hits.clear()
    return len(recent) > 60


def _top_genre(movies, games):
    counts = {}
    for item in list(movies) + list(games):
        for part in item["genre"].split("/"):
            part = part.strip()
            if part:
                counts[part] = counts.get(part, 0) + 1
    return max(counts, key=counts.get) if counts else ""


@app.route("/friends")
def friends():
    q = request.args.get("q", "").strip()[:24]
    me = g.user["id"] if g.user else 0
    results = userdb.search_users(q, 20, exclude_id=me) if len(q) >= 2 else []
    my_friends = userdb.friends_of(me) if me else []
    return render_template("friends.html", q=q, results=results, my_friends=my_friends,
                           friend_ids={r["id"] for r in my_friends})


@app.get("/api/users")
def api_users():
    if _search_throttled():
        return jsonify(error="Слишком много запросов. Подожди минуту."), 429
    q = request.args.get("q", "").strip()[:24]
    me = g.user["id"] if g.user else 0
    if len(q) < 2:
        return jsonify(items=[], short=True, logged=bool(me))
    fids = userdb.friend_ids(me) if me else set()
    items = [{"id": r["id"], "username": r["username"], "display_name": r["display_name"],
              "has_avatar": bool(r["has_avatar"]), "avatar_v": r["avatar_v"],
              "show_stats": bool(r["show_stats"]), "favs": r["favs"], "views": r["views"],
              "friend": r["id"] in fids}
             for r in userdb.search_users(q, 20, exclude_id=me)]
    return jsonify(items=items, short=False, logged=bool(me))


@app.route("/u/<username>")
def public_profile(username):
    row = userdb.get_user_by_username(username)
    if row is None:
        abort(404)
    own = bool(g.user) and g.user["id"] == row["id"]
    visible = bool(row["show_stats"]) or own
    ctx = dict(p=row, own=own, visible=visible, is_friend=False, stats=None,
               fav_movies=[], fav_games=[], top_genre="", total_fav_movies=0, total_fav_games=0)
    if g.user and not own:
        ctx["is_friend"] = userdb.is_friend(g.user["id"], row["id"])
    if visible:
        uid = row["id"]
        movies = [MOVIES[i] for i in userdb.favorite_ids(uid, "movie") if i < len(MOVIES)]
        games = [GAMES[i] for i in userdb.favorite_ids(uid, "game") if i < len(GAMES)]
        seen = [MOVIES[i] for i, _ in userdb.history_items(uid) if i < len(MOVIES)]
        ctx.update(stats=userdb.user_stats(uid), fav_movies=movies[:12], fav_games=games[:12],
                   total_fav_movies=len(movies), total_fav_games=len(games),
                   top_genre=_top_genre(movies + seen, games))
    return render_template("public_profile.html", **ctx)


@app.post("/friends/add/<int:uid>")
@login_required
def friend_add(uid):
    if userdb.add_friend(g.user["id"], uid):
        flash("Добавлено в друзья ✅", "success")
    else:
        flash("Не удалось добавить пользователя.", "error")
    return redirect(safe_next(request.form.get("next"), url_for("friends")))


@app.post("/friends/remove/<int:uid>")
@login_required
def friend_remove(uid):
    userdb.remove_friend(g.user["id"], uid)
    flash("Убрано из друзей.", "info")
    return redirect(safe_next(request.form.get("next"), url_for("friends")))


@app.route("/places")
def places():
    return render_template("places.html")

@app.route("/challenges")
def challenges():
    category = request.args.get("category", "all")
    if category not in CHALLENGE_CATEGORIES:
        category = "all"
    items = CHALLENGES if category == "all" else [x for x in CHALLENGES if x[2] == category]
    return render_template("challenges.html", challenges=items, category=category)


def plural_sets(value):
    """'3–4' -> '3–4 подхода', '1' -> '1 подход', '6' -> '6 подходов'."""
    n = int(re.findall(r"\d+", value)[-1])
    if n % 10 == 1 and n % 100 != 11:
        word = "подход"
    elif 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        word = "подхода"
    else:
        word = "подходов"
    return f"{value} {word}"


def format_exercise(e, level):
    name, muscles, equipment, sets, reps = e
    timed = "сек" in reps or "мин" in reps
    if sets == "1" and timed:
        detail = reps
    elif timed:
        detail = f"{plural_sets(sets)} · {reps}"
    elif reps.endswith("на ногу"):
        detail = f"{plural_sets(sets)} · {reps[:-len('на ногу')].strip()} повторений на ногу"
    else:
        detail = f"{plural_sets(sets)} · {reps} повторений"
    return {"name": name, "muscles": muscles, "equipment": equipment, "detail": detail}


# Fitness filters: each goal has its own exercise pool.  We keep the
# source data compact (name, muscles, equipment, sets, reps) and derive
# tags from it so the selected filters always have a meaningful result.
GOAL_TAGS = {
    "muscle": {
        "Жим лёжа со штангой", "Жим гантелей лёжа", "Жим гантелей на наклонной скамье",
        "Разводка с гантелями", "Сведение рук в тренажёре", "Отжимания",
        "Подтягивания", "Тяга верхнего блока", "Тяга горизонтального блока",
        "Тяга штанги в наклоне", "Тяга гантели одной рукой", "Жим ногами",
        "Приседания со штангой", "Гакк-присед", "Разгибание ног", "Сгибание ног лёжа",
        "Румынская тяга", "Выпады с гантелями", "Ягодичный мост", "Жим гантелей сидя",
        "Жим штанги над головой", "Разведения гантелей в стороны", "Обратная бабочка",
        "Тяга каната к лицу", "Подъём штанги на бицепс", "Сгибание рук с гантелями",
        "Молотковые сгибания", "Разгибание рук на блоке", "Французский жим",
        "Разгибание руки с гантелью из-за головы", "Скручивания", "Подъём коленей в упоре",
        "Подъём ног в висе", "Планка", "Ролик для пресса", "Подъём на носки стоя"
    },
    "strength": {
        "Жим лёжа со штангой", "Приседания со штангой", "Румынская тяга", "Тяга штанги в наклоне",
        "Жим штанги над головой", "Подтягивания", "Жим ногами", "Ягодичный мост", "Отжимания",
        "Жим гантелей лёжа", "Тяга верхнего блока", "Тяга горизонтального блока"
    },
    "fatloss": {
        "Бёрпи", "Прыжки на тумбу", "Канаты", "Гребля", "Беговая дорожка", "Велотренажёр",
        "Эллиптический тренажёр", "Степпер", "Приседания со штангой", "Выпады с гантелями",
        "Жим ногами", "Отжимания", "Подтягивания", "Планка", "Скручивания"
    },
    "fitness": {
        # General fitness intentionally covers every major movement/muscle group,
        # so secondary filters do not silently produce an empty list.
        "Отжимания", "Приседания со штангой", "Выпады с гантелями", "Ягодичный мост",
        "Тяга верхнего блока", "Подтягивания", "Жим гантелей лёжа", "Жим гантелей сидя", "Скручивания",
        "Планка", "Бёрпи", "Гребля", "Беговая дорожка", "Велотренажёр", "Эллиптический тренажёр",
        "Подъём на носки стоя", "Сгибание рук с гантелями", "Разгибание рук на блоке",
        "Румынская тяга", "Тяга гантели одной рукой", "Разведения гантелей в стороны",
        "Сгибание ног лёжа", "Гиперэкстензия", "Ролик для пресса", "Прыжки на тумбу", "Канаты", "Степпер", "Подъём коленей в упоре", "Подъём ног в висе"
    },
    "endurance": {
        "Бёрпи", "Прыжки на тумбу", "Канаты", "Гребля", "Беговая дорожка", "Велотренажёр",
        "Эллиптический тренажёр", "Степпер", "Планка", "Отжимания", "Приседания со штангой",
        "Выпады с гантелями"
    },
}

STRENGTH_MAIN = GOAL_TAGS["strength"]

# Beginner-safe exclusions. Intermediate and advanced can use the full pool.
LEVEL_EXCLUDE = {
    "beginner": {"Подъём ног в висе", "Прыжки на тумбу", "Ролик для пресса", "Жим штанги над головой",
                  "Подтягивания", "Бёрпи"},
    "intermediate": set(),
    "advanced": set(),
}
# Exact secondary filters. Unlike the goal filter, these are based on explicit
# exercise metadata, so e.g. "гантели" never accidentally matches a barbell exercise.
MUSCLE_TAGS = {
    "Грудь": {"Жим лёжа со штангой", "Жим гантелей лёжа", "Жим гантелей на наклонной скамье", "Разводка с гантелями", "Сведение рук в тренажёре", "Отжимания"},
    "Спина": {"Подтягивания", "Тяга верхнего блока", "Тяга горизонтального блока", "Тяга штанги в наклоне", "Тяга гантели одной рукой", "Тяга каната к лицу"},
    "Плечи": {"Жим гантелей сидя", "Жим штанги над головой", "Разведения гантелей в стороны", "Обратная бабочка", "Тяга каната к лицу"},
    "Бицепс": {"Подтягивания", "Подъём штанги на бицепс", "Сгибание рук с гантелями", "Молотковые сгибания"},
    "Трицепс": {"Жим лёжа со штангой", "Жим гантелей лёжа", "Отжимания", "Разгибание рук на блоке", "Французский жим", "Разгибание руки с гантелью из-за головы"},
    "Квадрицепс": {"Жим ногами", "Приседания со штангой", "Гакк-присед", "Разгибание ног", "Выпады с гантелями", "Прыжки на тумбу"},
    "Ягодицы": {"Приседания со штангой", "Выпады с гантелями", "Ягодичный мост", "Гиперэкстензия", "Румынская тяга", "Прыжки на тумбу"},
    "Бицепс бедра": {"Сгибание ног лёжа", "Румынская тяга", "Гиперэкстензия"},
    "Икры": {"Подъём на носки стоя"},
    "Пресс / кор": {"Скручивания", "Подъём коленей в упоре", "Подъём ног в висе", "Планка", "Ролик для пресса", "Бёрпи"},
    "Всё тело": {"Бёрпи", "Канаты", "Гребля"},
    "Кардио": {"Бёрпи", "Прыжки на тумбу", "Канаты", "Гребля", "Беговая дорожка", "Велотренажёр", "Эллиптический тренажёр", "Степпер"},
}

EQUIPMENT_TAGS = {
    # These are capability tags, not exact equipment-name matches. An exercise
    # can require more than one item (e.g. dumbbells + bench), so selecting an
    # equipment type returns every exercise that can be performed with it.
    "Собственный вес": {
        "Отжимания", "Подтягивания", "Скручивания", "Подъём коленей в упоре",
        "Подъём ног в висе", "Планка", "Бёрпи"
    },
    "Гантели": {
        "Жим гантелей лёжа", "Жим гантелей на наклонной скамье", "Разводка с гантелями",
        "Тяга гантели одной рукой", "Выпады с гантелями", "Жим гантелей сидя",
        "Разведения гантелей в стороны", "Сгибание рук с гантелями", "Молотковые сгибания",
        "Разгибание руки с гантелью из-за головы", "Подъём на носки стоя", "Французский жим"
    },
    "Штанга": {
        "Жим лёжа со штангой", "Тяга штанги в наклоне", "Приседания со штангой",
        "Румынская тяга", "Жим штанги над головой", "Подъём штанги на бицепс",
        "Ягодичный мост", "Французский жим"
    },
    "Тренажёры": {
        "Сведение рук в тренажёре", "Тяга верхнего блока", "Тяга горизонтального блока",
        "Жим ногами", "Гакк-присед", "Разгибание ног", "Сгибание ног лёжа",
        "Ягодичный мост", "Подъём на носки стоя", "Обратная бабочка", "Гиперэкстензия",
        "Гребля", "Беговая дорожка", "Велотренажёр", "Эллиптический тренажёр", "Степпер"
    },
    "Кроссовер / блок": {
        "Тяга верхнего блока", "Тяга горизонтального блока", "Тяга каната к лицу",
        "Разгибание рук на блоке"
    },
    "Турник / брусья": {
        "Подтягивания", "Подъём коленей в упоре", "Подъём ног в висе"
    },
    "Скамья / коврик": {
        "Жим лёжа со штангой", "Жим гантелей лёжа", "Жим гантелей на наклонной скамье",
        "Разводка с гантелями", "Тяга гантели одной рукой", "Жим гантелей сидя",
        "Скручивания", "Планка"
    },
    "Кардио-тренажёр": {
        "Гребля", "Беговая дорожка", "Велотренажёр", "Эллиптический тренажёр", "Степпер"
    },
    "Спецоборудование": {
        "Гиперэкстензия", "Ролик для пресса", "Прыжки на тумбу", "Канаты"
    },
}


GOALS = set(GOAL_TAGS)
LEVELS = {"beginner", "intermediate", "advanced"}
MUSCLES = list(MUSCLE_TAGS.keys())
EQUIPMENT = list(EQUIPMENT_TAGS.keys())


def exercise_matches_goal(exercise, goal):
    return exercise[0] in GOAL_TAGS[goal]


def exercise_has_tag(name, mapping, tag):
    return name in mapping.get(tag, set())


@app.route("/fitness")
def fitness():
    goal = request.args.get("goal", "fitness")
    level = request.args.get("level", "beginner")
    selected_muscles = [x for x in request.args.getlist("muscle") if x in MUSCLES]
    selected_equipment = [x for x in request.args.getlist("equipment") if x in EQUIPMENT]
    if goal not in GOALS:
        goal = "fitness"
    if level not in LEVELS:
        level = "beginner"

    items = []
    for e in FITNESS_EXERCISES:
        name = e[0]
        if not exercise_matches_goal(e, goal) or name in LEVEL_EXCLUDE[level]:
            continue
        # Multiple selections are OR inside a filter group: any selected muscle
        # and any selected equipment must match. Across groups the logic is AND.
        if selected_muscles and not any(exercise_has_tag(name, MUSCLE_TAGS, m) for m in selected_muscles):
            continue
        if selected_equipment and not any(exercise_has_tag(name, EQUIPMENT_TAGS, q) for q in selected_equipment):
            continue
        items.append(e)

    if goal in ("fatloss", "endurance"):
        items.sort(key=lambda e: 0 if e[0] in MUSCLE_TAGS["Кардио"] else 1)
    return render_template("fitness.html", exercises=[format_exercise(e, level) for e in items],
                           goal=goal, level=level, muscles=MUSCLES, equipment=EQUIPMENT,
                           selected_muscles=selected_muscles, selected_equipment=selected_equipment,
                           result_count=len(items))


def _public_base():
    """Адрес сайта, который «зашивается» в APK (домен, с которого его скачали)."""
    env = os.getenv("LIVO_PUBLIC_URL", "").strip()
    if env:
        return env
    base = request.url_root.rstrip("/")
    host = request.host.split(":")[0]
    local = host in ("localhost", "127.0.0.1") or re.fullmatch(r"\d+\.\d+\.\d+\.\d+", host)
    if base.startswith("http://") and not local:
        base = "https://" + base[len("http://"):]
    return base


@app.route("/app")
def app_page():
    return render_template("app.html")


@app.get("/livo.apk")
def download_apk():
    static_apk = os.path.join(app.root_path, "static", "LIVO.apk")
    if os.path.isfile(static_apk):
        resp = send_file(static_apk, mimetype="application/vnd.android.package-archive",
                         as_attachment=True, download_name="LIVO.apk")
        resp.headers["Cache-Control"] = "no-cache"
        return resp
    try:
        import livo_apk
        data = livo_apk.build_apk(_public_base())
    except Exception:
        app.logger.exception("APK build failed")
        abort(503)
    resp = Response(data, mimetype="application/vnd.android.package-archive")
    resp.headers["Content-Disposition"] = 'attachment; filename="LIVO.apk"'
    resp.headers["Content-Length"] = str(len(data))
    resp.headers["Cache-Control"] = "no-cache"
    return resp


@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/privacy")
def privacy():
    return render_template("privacy.html")

@app.route("/social")
def social():
    return render_template("social.html")



@app.route("/policy")
def policy():
    return render_template("policy.html")

@app.get("/healthz")
def healthz():
    return {"status": "ok"}, 200

@app.route("/pc-builder")
def pc_builder():
    gpu = request.args.get("gpu", "RTX 4070 SUPER")
    resolution = request.args.get("resolution", "1440p")
    games = FPS_PROFILES.get(gpu, FPS_PROFILES["RTX 4070 SUPER"]).get(resolution, {})
    return render_template("pc_builder.html", parts=PC_PARTS, gpu=gpu, resolution=resolution, games=games)


@app.route("/recipes")
def recipes():
    category = request.args.get("category", "all")
    level = request.args.get("level", "all")
    items = RECIPES
    if category != "all":
        items = [r for r in items if r[2] == category]
    if level != "all":
        items = [r for r in items if r[1] == level]
    return render_template("recipes.html", recipes=items, category=category, level=level)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=os.getenv("FLASK_DEBUG") == "1")
