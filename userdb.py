"""Хранилище пользователей LIVO: аккаунты, избранное, история, аватары (SQLite)."""
import os
import secrets
import sqlite3
import time
from pathlib import Path

DATA_DIR = Path(os.getenv("LIVO_DATA_DIR", Path(__file__).resolve().parent))
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "livo_users.db"
HISTORY_LIMIT = 100

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE COLLATE NOCASE,
    username TEXT NOT NULL UNIQUE COLLATE NOCASE,
    pw_hash TEXT NOT NULL,
    display_name TEXT NOT NULL DEFAULT '',
    bio TEXT NOT NULL DEFAULT '',
    avatar BLOB,
    avatar_mime TEXT,
    avatar_v INTEGER NOT NULL DEFAULT 0,
    theme TEXT NOT NULL DEFAULT 'auto',
    created_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS favorites (
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    kind TEXT NOT NULL CHECK(kind IN ('movie','game')),
    item_id INTEGER NOT NULL,
    created_at INTEGER NOT NULL,
    PRIMARY KEY (user_id, kind, item_id)
);
CREATE TABLE IF NOT EXISTS history (
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    movie_id INTEGER NOT NULL,
    viewed_at INTEGER NOT NULL,
    PRIMARY KEY (user_id, movie_id)
);
"""


def connect():
    con = sqlite3.connect(DB_PATH, timeout=10)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def init_db():
    with connect() as con:
        con.executescript(SCHEMA)


def secret_key():
    """SECRET_KEY из окружения или постоянный ключ в файле (сессии переживают перезапуск)."""
    env = os.getenv("SECRET_KEY")
    if env:
        return env
    path = DATA_DIR / ".secret_key"
    if path.exists():
        return path.read_text().strip()
    key = secrets.token_hex(32)
    path.write_text(key)
    return key


# ---------- пользователи ----------
def create_user(email, username, pw_hash):
    with connect() as con:
        cur = con.execute(
            "INSERT INTO users(email, username, pw_hash, display_name, created_at) VALUES(?,?,?,?,?)",
            (email, username, pw_hash, username, int(time.time())),
        )
        return cur.lastrowid


def get_user(uid):
    with connect() as con:
        return con.execute(
            "SELECT id,email,username,pw_hash,display_name,bio,avatar_mime,avatar_v,theme,created_at,"
            "(avatar IS NOT NULL) AS has_avatar FROM users WHERE id=?", (uid,)
        ).fetchone()


def find_user(login):
    with connect() as con:
        return con.execute(
            "SELECT id,pw_hash FROM users WHERE email=? OR username=?", (login, login)
        ).fetchone()


def exists(field, value, exclude_id=0):
    assert field in ("email", "username")
    with connect() as con:
        return con.execute(
            f"SELECT 1 FROM users WHERE {field}=? AND id!=?", (value, exclude_id)
        ).fetchone() is not None


def update_profile(uid, display_name, bio, username, email):
    with connect() as con:
        con.execute(
            "UPDATE users SET display_name=?, bio=?, username=?, email=? WHERE id=?",
            (display_name, bio, username, email, uid),
        )


def set_password(uid, pw_hash):
    with connect() as con:
        con.execute("UPDATE users SET pw_hash=? WHERE id=?", (pw_hash, uid))


def set_theme(uid, theme):
    with connect() as con:
        con.execute("UPDATE users SET theme=? WHERE id=?", (theme, uid))


def set_avatar(uid, data, mime):
    with connect() as con:
        if data is None:
            con.execute("UPDATE users SET avatar=NULL, avatar_mime=NULL, avatar_v=avatar_v+1 WHERE id=?", (uid,))
        else:
            con.execute("UPDATE users SET avatar=?, avatar_mime=?, avatar_v=avatar_v+1 WHERE id=?", (data, mime, uid))


def get_avatar(uid):
    with connect() as con:
        return con.execute("SELECT avatar, avatar_mime, avatar_v FROM users WHERE id=?", (uid,)).fetchone()


def delete_user(uid):
    with connect() as con:
        con.execute("DELETE FROM users WHERE id=?", (uid,))


# ---------- избранное ----------
def toggle_favorite(uid, kind, item_id):
    """Возвращает True, если элемент теперь в избранном."""
    with connect() as con:
        row = con.execute(
            "SELECT 1 FROM favorites WHERE user_id=? AND kind=? AND item_id=?", (uid, kind, item_id)
        ).fetchone()
        if row:
            con.execute("DELETE FROM favorites WHERE user_id=? AND kind=? AND item_id=?", (uid, kind, item_id))
            return False
        con.execute(
            "INSERT INTO favorites(user_id,kind,item_id,created_at) VALUES(?,?,?,?)",
            (uid, kind, item_id, int(time.time())),
        )
        return True


def favorite_ids(uid, kind):
    with connect() as con:
        rows = con.execute(
            "SELECT item_id FROM favorites WHERE user_id=? AND kind=? ORDER BY created_at DESC", (uid, kind)
        ).fetchall()
    return [r["item_id"] for r in rows]


# ---------- история ----------
def add_history(uid, movie_id):
    now = int(time.time())
    with connect() as con:
        con.execute(
            "INSERT INTO history(user_id,movie_id,viewed_at) VALUES(?,?,?) "
            "ON CONFLICT(user_id,movie_id) DO UPDATE SET viewed_at=excluded.viewed_at",
            (uid, movie_id, now),
        )
        con.execute(
            "DELETE FROM history WHERE user_id=? AND movie_id NOT IN "
            "(SELECT movie_id FROM history WHERE user_id=? ORDER BY viewed_at DESC LIMIT ?)",
            (uid, uid, HISTORY_LIMIT),
        )


def history_items(uid):
    with connect() as con:
        rows = con.execute(
            "SELECT movie_id, viewed_at FROM history WHERE user_id=? ORDER BY viewed_at DESC", (uid,)
        ).fetchall()
    return [(r["movie_id"], r["viewed_at"]) for r in rows]


def clear_history(uid):
    with connect() as con:
        con.execute("DELETE FROM history WHERE user_id=?", (uid,))
