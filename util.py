import time, os, sqlite3, requests
from bs4 import BeautifulSoup
from yt_dlp import YoutubeDL
from chat_downloader.sites import YouTubeChatDownloader

from models import User, Channel

DB_PATH = "data/queries.db"
COOKIES_FILE = "/tmp/cookies.txt"

role_icons = {"moderator": "🛡️", "owner": "👑", "member": "💎", "": ""}


def get_channel_avatar(channel_id):
    try:
        html = requests.get(f"https://www.youtube.com/channel/{channel_id}", timeout=5).text
        soup = BeautifulSoup(html, "html.parser")
        return soup.find("meta", property="og:image")["content"]
    except Exception as e:
        print("❌ Avatar fetch failed:", e)
        return None


def get_stream_metadata(channel_id, chat_id=None):
    import scrapetube

    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS chat_mapping (chat TEXT, video TEXT)")
        if chat_id:
            cur.execute("SELECT video FROM chat_mapping WHERE chat=?", (chat_id,))
            row = cur.fetchone()
            if row:
                vid = row[0]
                return YouTubeChatDownloader(cookies=COOKIES_FILE).get_video_data(video_id=vid)
        vids = scrapetube.get_channel(channel_id, content_type="streams", limit=3)
        for vid in vids:
            if vid["thumbnailOverlays"][0]["thumbnailOverlayTimeStatusRenderer"]["style"] == "LIVE":
                vid_id = vid["videoId"]
                meta = YouTubeChatDownloader(cookies=COOKIES_FILE).get_video_data(video_id=vid_id)
                if chat_id:
                    cur.execute("REPLACE INTO chat_mapping VALUES (?, ?)", (chat_id, vid_id))
                    conn.commit()
                conn.close()
                print("🎥 Live stream found:", vid_id)
                return meta
    except Exception as e:
        print("❌ scrapetube or YTCD failed:", e)

    return None


def hms(seconds):
    h = seconds // 3600
    m = (seconds % 3600) % 60
    s = seconds % 60
    return f"{h}:{m:02}:{s:02}"


def send_discord_webhook(clip_id, title, hms_time, url, delay, user, channel):
    if not channel.webhook:
        return False

    avatar_url = get_channel_avatar(user.id)
    username = f"{user.name} {role_icons.get(user.level, '')}".strip()
    message = f"{clip_id} | {title}\n\n{hms_time}\n{url}\n\nDelayed by {delay} seconds."

    payload = {
        "username": username,
        "content": message
    }

    if avatar_url:
        payload["avatar_url"] = avatar_url

    try:
        resp = requests.post(channel.webhook, json=payload)
        if resp.status_code in [200, 204]:
            # Cache message ID to DB
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute("CREATE TABLE IF NOT EXISTS sent (clip TEXT PRIMARY KEY, message TEXT, webhook TEXT)")
            try:
                msg_id = resp.json()["id"]
            except:
                msg_id = None
            cur.execute("REPLACE INTO sent VALUES (?, ?, ?)", (clip_id, msg_id, channel.webhook))
            conn.commit()
            conn.close()
            return True
    except Exception as e:
        print("❌ Webhook failed:", e)

    return False


def delete_from_discord(clip_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT message, webhook FROM sent WHERE clip=?", (clip_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return False

    message_id, webhook_url = row
    if message_id and webhook_url:
        try:
            r = requests.delete(f"{webhook_url}/messages/{message_id}")
            print(f"🗑️ Deleted clip {clip_id} from Discord")
            return r.status_code in [200, 204]
        except Exception as e:
            print("❌ Delete failed:", e)

    return False
