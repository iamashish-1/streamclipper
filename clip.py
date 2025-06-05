import time
import sqlite3
from util import *
from models import User, Channel
from chat_downloader import ChatDownloader

def create_clip(chat_id, query, headers):
    user = User(headers.get("Nightbot-User", ""))
    title = get_clip_title(query)
    channel = Channel(headers.get("Nightbot-Channel", "").split("=")[-1])

    stream = get_video_for_channel(channel.id)
    if not stream:
        return "❌ No LiveStream Found. or failed to fetch the stream. Please try again later."

    try:
        chat_iter = ChatDownloader().get_chat(stream["original_video_id"])
        matched = None
        for chat in chat_iter:
            if chat["message_id"] == chat_id:
                matched = chat
                break
    except Exception as e:
        return f"❌ ChatDownloader error: {e}"

    if not matched:
        return "❌ Chat message not found in stream chat."

    timestamp_usec = matched["timestamp"]
    stream_start_usec = stream["start_time"]
    offset_sec = round((timestamp_usec - stream_start_usec) / 1_000_000)

    delay = int(headers.get("delay", -30))
    final_time = offset_sec + delay
    clip_id = generate_clip_id(chat_id, timestamp_usec)
    hms = seconds_to_hms(final_time)
    url = f"https://youtu.be/{stream['original_video_id']}?t={final_time}"

    avatar = get_avatar(user.id)
    msg_id = send_discord_webhook(clip_id, title, hms, url, delay, user, avatar, stream["original_video_id"])

    if msg_id:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS clips (clip_id TEXT, video_id TEXT, message_id TEXT)")
        cur.execute("REPLACE INTO clips VALUES (?, ?, ?)", (clip_id, stream["original_video_id"], msg_id))
        conn.commit()
        conn.close()

    return url

def delete_clip(clip_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT video_id, message_id FROM clips WHERE clip_id=?", (clip_id,))
    row = cur.fetchone()
    if row:
        video_id, msg_id = row
        delete_discord_message(video_id, msg_id)
        cur.execute("DELETE FROM clips WHERE clip_id=?", (clip_id,))
        conn.commit()
    conn.close()
    return "🗑️ Deleted clip successfully."
