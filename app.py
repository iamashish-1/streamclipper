import os
import sqlite3
from flask import Flask, request, redirect, render_template, session
from clip import create_clip, delete_clip
from auth import login_required
from dotenv import load_dotenv
from discord_webhook import DiscordEmbed, DiscordWebhook

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")

DB_PATH = "data/queries.db"
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

# Ensuring required tables exist
print("Running init.db ---- ")
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            channel TEXT PRIMARY KEY,
            webhook TEXT
        )""")
        cur.execute("""
        CREATE TABLE IF NOT EXISTS clips (
            clip_id TEXT PRIMARY KEY,
            channel TEXT,
            message_id TEXT,
            time_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        conn.commit()

#-- We'll always initiate db to make sure table exists
@app.before_request
def before_every_request():
    init_db()
    session.permanent = False  # session will expire when browser closes

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

    #- sending discord welcome embed
        try:
            logo = os.getenv("LOGO")
            wh = DiscordWebhook(url = webhook, username = "StreamClipper", avatar_url = logo)
            embed = DiscordEmbed(
                title="Welcome to StreamCliper !!!!",
                description=(
                    "This channel is configured to get clips from your YouTube Live.\n"
                    "Sit back, stream, and we’ll handle the highlights on your call!"
                ),
                color="FF0000"
            )
            embed.set_image(url=logo)
            embed.set_footer(text="StreamClipper is live and listening.", icon_url=logo)
            wh.add_embed(embed)
            wh.execute()
            print("Channel configuration message sent to discord via webhook")
        except Exception as e:
            print("⚠️ Failed to send configuration message to discord")
    cur.execute("SELECT * FROM settings")
    data = cur.fetchall()
    conn.close()
    return render_template("settings.html", data=data)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
