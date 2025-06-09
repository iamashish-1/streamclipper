import os
import sqlite3
from flask import Flask, request, redirect, render_template, session
from clip import create_clip, delete_clip
from auth import login_required
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")

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

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user, pw = request.form["username"], request.form["password"]
        if user == os.getenv("ADMIN_USER") and pw == os.getenv("ADMIN_PASS"):
            session["admin"] = True
            return redirect("/settings")
        return render_template("login.html", error="❌ Invalid credentials.")
    return render_template("login.html")

@app.route("/settings", methods=["GET", "POST"])

def settings():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS settings (channel TEXT PRIMARY KEY, webhook TEXT)")
    if request.method == "POST":
        cur.execute("REPLACE INTO settings VALUES (?, ?)", (
            request.form["channel"], request.form["webhook"]))
        conn.commit()
    cur.execute("SELECT * FROM settings")
    data = cur.fetchall()
    conn.close()
    return render_template("settings.html", data=data)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")
