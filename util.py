import os
import time
import sqlite3
import requests
from bs4 import BeautifulSoup
from yt_dlp import YoutubeDL
from chat_downloader.sites import YouTubeChatDownloader
import scrapetube
from models import Channel, User

DB_PATH = "data/queries.db"
COOKIES_FILE = "/tmp/cookies.txt"

role_icons = {
    "moderator": "🛡️",
    "owner": "👑",
    "member": "💎",
    "": ""
}

def get_avatar(channel_id):
    try:
        url = f"https://www.youtube.com/channel/{channel_id}"
        r = requests.get(url, timeout=5)
        soup = BeautifulSoup(r.text, "html.parser")
        return soup.find("meta", property="og:image")["content"]
    except Exception as e:
        print("⚠️ Failed to fetch avatar:", e)
        return None

def get_video_for_channel(channel_id):
    try:
        print("🔍 Checking live videos for:", channel_id)
        videos = scrapetube.get_channel(channel_id, content_type="streams", limit=3)
        for vid in videos:
            overlays = vid.get("thumbnailOverlays", [{}])
            if overlays and overlays[0].get("thumbnailOverlayTimeStatusRenderer", {}).get("style") == "LIVE":
                vid_id = vid["videoId"]
                print("🎥 Live stream found:", vid_id)
                try:
                    stream = YouTubeChatDownloader(cookies=COOKIES_FILE).get_video_data(video_id=vid_id)
                    print(f"Meta data fetched : {stream}")
                    return stream
                except Exception as e:
                    print("⚠️ ChatDownloader failed for", vid_id, ":", e)
    except Exception as e:
        print("❌ scrapetube or YTCD failed:", e)

    print("⚠️ No valid live video found.")
    return None

def generate_clip_id(chat_id, timestamp):
    return chat_id[-3:].upper() + str(timestamp % 100000)

def seconds_to_hms(seconds):
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h}:{m:02}:{s:02}"

def send_discord_webhook(clip_id, title, hms, url, delay, user, avatar, video_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS settings (channel TEXT PRIMARY KEY, webhook TEXT)")
    cur.execute("SELECT webhook FROM settings WHERE channel=?", (video_id,))
    row = cur.fetchone()
    conn.close()

    if not row:
        return None

    webhook = row[0]
    emoji = role_icons.get(user.level, "")
    username = f"{user.name} {emoji}".strip()

    message = f"{clip_id} | {title}\n\n{hms}\n{url}\n\nDelayed by {delay} seconds."
    payload = {
        "username": username,
        "content": message
    }
    if avatar:
        payload["avatar_url"] = avatar

    try:
        r = requests.post(webhook, json=payload)
        if r.status_code in [200, 204]:
            return r.headers.get("X-Message-ID")
    except Exception as e:
        print("Webhook error:", e)
    return None

def delete_discord_message(video_id, message_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT webhook FROM settings WHERE channel=?", (video_id,))
    row = cur.fetchone()
    conn.close()

    if row:
        webhook = row[0].rstrip("/")
        try:
            r = requests.delete(f"{webhook}/messages/{message_id}")
            return r.status_code == 204
        except Exception as e:
            print("Webhook delete error:", e)
    return False

def get_clip_title(query):
    return query.replace("+", " ") if query else "Untitled"
