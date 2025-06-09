import os
import sqlite3
from flask import Flask, request, redirect, render_template, session
from clip import create_clip, delete_clip
from auth import login_required
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "streamclipper_dev_secret")

DB_PATH = "data/queries.db"
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

@app.route("/")
def home():
    return "✅ StreamClipper is running."

@app.route("/clip/<chat_id>/<query>")
def clip(chat_id, query):
    return create_clip(chat_id, query, request.headers)

@app.route("/delete/<clip_id>")
def delete(clip_id):
    return delete_clip(clip_id)

@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS settings (channel TEXT PRIMARY KEY, webhook TEXT)")
    if request.method == "POST":
        channel = request.form.get("channel", "").strip()
        webhook = request.form.get("webhook", "").strip()
        if channel and webhook:
            cur.execute("REPLACE INTO settings (channel, webhook) VALUES (?, ?)", (channel, webhook))
            conn.commit()
    rows = cur.execute("SELECT * FROM settings").fetchall()
    conn.close()
    return render_template("settings.html", rows=rows)

@app.route("/webhooks")
@login_required
def webhooks():
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT * FROM settings").fetchall()
    conn.close()
    return render_template("webhooks.html", rows=rows)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = request.form["username"]
        p = request.form["password"]
        if u == os.getenv("ADMIN_USER") and p == os.getenv("ADMIN_PASS"):
            session["admin"] = True
            return redirect("/settings")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")
