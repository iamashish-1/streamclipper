import os, sqlite3, shutil
from flask import Flask, request, render_template, redirect, session
from clip import create_clip, delete_clip
from auth import login_required
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "default_secret")

DB_PATH = "data/queries.db"
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

# Ensure /tmp/cookies.txt is copied
try:
    os.makedirs("/tmp", exist_ok=True)
    shutil.copy("/etc/secrets/cookies.txt", "/tmp/cookies.txt")
except Exception as e:
    print("❌ cookies.txt not found:", e)

@app.route("/")
def index():
    return "✅ StreamClipper running."

@app.route("/clip/<chatid>/<query>")
def clip(chatid, query):
    return create_clip(chatid, query, request.headers)

@app.route("/delete/<clip_id>")
def delete(clip_id):
    return delete_clip(clip_id)

@app.route("/login", methods=["GET", "POST"])
def login():
    from flask import request, render_template
    if request.method == "POST":
        u, p = request.form["username"], request.form["password"]
        if u == os.getenv("ADMIN_USER") and p == os.getenv("ADMIN_PASS"):
            session["admin"] = True
            return redirect("/settings")
        return render_template("login.html", error="Invalid credentials")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS settings (channel TEXT PRIMARY KEY, webhook TEXT)")
    if request.method == "POST":
        channel = request.form["channel"]
        webhook = request.form["webhook"]
        cur.execute("REPLACE INTO settings VALUES (?, ?)", (channel, webhook))
        conn.commit()
    cur.execute("SELECT * FROM settings")
    data = cur.fetchall()
    conn.close()
    return render_template("settings.html", data=data)
