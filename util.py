import os
import sqlite3
import requests
from urllib.parse import parse_qs
from bs4 import BeautifulSoup
from chat_downloader.sites import YouTubeChatDownloader
import scrapetube
from models import User

DB_PATH = "data/queries.db"
COOKIES_FILE = os.getenv("YOUTUBE_COOKIES")

role_icons = {
    "moderator": "🛡️",
    "owner": "👑",
    "member": "💎",
    "": ""
}

def get_user_details_from_headers(headers):
    user_header = headers.get("Nightbot-User", "")
    qs = parse_qs(user_header)
    provider_id = qs.get("providerId", [""])[0]
    display_name = qs.get("displayName", ["Unknown"])[0].replace("+", " ")
    level = qs.get("userLevel", [""])[0].lower()

    user = User(provider_id, display_name, level)

    try:
        soup = BeautifulSoup(
            requests.get(f"https://youtube.com/channel/{user.id}", timeout=5).text,
            "html.parser"
        )
        user.avatar = soup.find("meta", property="og:image")["content"]
    except Exception as e:
        print("Failed to fetch avatar:", e)

    return user

def get_stream_metadata(channel_id, chat_id):
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS chat_mapping (chat TEXT, video TEXT)")
        cur.execute("SELECT video FROM chat_mapping WHERE chat=?", (chat_id,))
        row = cur.fetchone()
        conn.close()
        if row:
            vid_id = row[0]
            return YouTubeChatDownloader(cookies=COOKIES_FILE).get_video_data(video_id=vid_id)

        print(f"🔍 Checking live videos for: {channel_id}")
        vids = scrapetube.get_channel(channel_id, limit=3)
        for vid in vids:
            if vid["thumbnailOverlays"][0]["thumbnailOverlayTimeStatusRenderer"]["style"] == "LIVE":
                vid_id = vid["videoId"]
                print(f"🎥 Live stream found: {vid_id}")
                data = YouTubeChatDownloader(cookies=COOKIES_FILE).get_video_data(video_id=vid_id)

                conn = sqlite3.connect(DB_PATH)
                cur = conn.cursor()
                cur.execute("REPLACE INTO chat_mapping VALUES (?, ?)", (chat_id, vid_id))
                conn.commit()
                conn.close()
                print(data)
                return data
    except Exception as e:
        print("❌ scrapetube or YTCD failed:", e)

    print("⚠️ No valid live video found.")
    return None

def seconds_to_hms(seconds):
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h}:{m:02}:{s:02}"

def send_discord_webhook(clip_id, title, hms, url, delay, user, channel_id, video_id=None):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT webhook FROM settings WHERE channel=?", (channel_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return False

    webhook = row[0]
    emoji = role_icons.get(user.level.lower(), "")
    username = f"{user.name} {emoji}".strip()

    payload = {
        "username": username,
        "content": f"{clip_id} | **{title}**\n\n{hms}\n{url}\nDelayed by {delay} seconds."
    }

    if user.avatar and user.avatar.startswith("https://"):
        payload["avatar_url"] = user.avatar

    try:
        r = requests.post(webhook, json=payload)
        if r.status_code in [200, 204]:
            try:
                message_id = None
                if r.headers.get("Content-Type", "").startswith("application/json"):
                    try:
                        message_id = r.json().get("id")
                    except Exception as e:
                        print("⚠️ Could not parse Discord response JSON:", e)
                if message_id:
                    print("💾 Saving clip to DB:", clip_id, channel_id, message_id)
                    conn = sqlite3.connect(DB_PATH)
                    cur = conn.cursor()
                    cur.execute("INSERT OR REPLACE INTO clips (clip_id, channel, message_id) VALUES (?, ?, ?)", (
                        clip_id, channel_id, message_id
                    ))
                    conn.commit()
                    conn.close()
                else:
                    print("⚠️ No message ID returned from Discord")
        return r.status_code in [200, 204]
    except Exception as e:
        print("Webhook send error:", e)
        return False
