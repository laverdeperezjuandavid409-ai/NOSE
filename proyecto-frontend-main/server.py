import os
import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify, render_template, send_from_directory, g
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "gamevault.db")

app = Flask(__name__, template_folder="templates")

def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DB_PATH)
        db.row_factory = sqlite3.Row
    return db

def init_db():
    db = get_db()
    db.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)
    db.commit()

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()

@app.before_first_request
def startup():
    init_db()

# Serve index
@app.route("/")
def index():
    return render_template("base.html")

# Serve static files referenced from template (estilos.css, scripts.js, images)
@app.route("/estilos.css")
def estilos():
    return send_from_directory(BASE_DIR, "estilos.css")

@app.route("/scripts.js")
def scripts():
    return send_from_directory(BASE_DIR, "scripts.js")

@app.route("/images/<path:filename>")
def images(filename):
    images_dir = os.path.join(BASE_DIR, "images")
    return send_from_directory(images_dir, filename)

# API: register
@app.route("/api/register", methods=["POST"])
def api_register():
    data = request.get_json() or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    if not username or not password:
        return jsonify(ok=False, error="Usuario y contraseña requeridos"), 400
    db = get_db()
    try:
        pw_hash = generate_password_hash(password)
        db.execute("INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
                   (username, pw_hash, datetime.utcnow().isoformat()))
        db.commit()
        user = {"username": username}
        return jsonify(ok=True, user=user)
    except sqlite3.IntegrityError:
        return jsonify(ok=False, error="El usuario ya existe"), 400
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500

# API: login
@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json() or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    if not username or not password:
        return jsonify(ok=False, error="Usuario y contraseña requeridos"), 400
    db = get_db()
    cur = db.execute("SELECT * FROM users WHERE username = ?", (username,))
    row = cur.fetchone()
    if not row:
        return jsonify(ok=False, error="Usuario no encontrado"), 400
    if not check_password_hash(row["password_hash"], password):
        return jsonify(ok=False, error="Contraseña incorrecta"), 400
    user = {"username": row["username"]}
    return jsonify(ok=True, user=user)

if __name__ == "__main__":
    app.run(debug=True)
