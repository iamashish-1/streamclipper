import time
import sqlite3
from util import (
    get_video_for_channel,
    generate_clip_id,
    seconds_to_hms,
    send_discord_webhook,
    delete_discord_message,
    get_clip_title,
)
from models import User, Channel

DB_PATH = "data/queries.db"

def create_clip(chat_id, query, headers):
    user = User(headers)
    channel_id = chat_id[:24]
    channel = Channel(channel_id)

    stream = get_video_for_channel(channel_id)
    if not stream:
        return "⚠️ No valid live video found."

    start_usec = stream.get("start_time")
    if not start_usec:
        return "⚠️ Could not determine stream start time."

    timestamp = int(time.time() * 1_000_000)
    seconds_offset = int((timestamp - start_usec) / 1_000_000)
    delay = int(headers.get("delay", -30))

    clip_time = max(0, seconds_offset + delay)
    hms = seconds_to_hms(clip_time)
    url = f"https://youtu.be/{stream['original_video_id']}?t={clip_time}"
    title = get_clip_title(query)

    clip_id = generate_clip_id(chat_id, timestamp)

    message_id = send_discord_webhook(
        clip_id, title, hms, url, delay, user, user.id, stream["original_video_id"]
    )

    if message_id:
        # Cache chat_id → video_id
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS chat_mapping (chat TEXT PRIMARY KEY, video TEXT)")
        cur.execute("REPLACE INTO chat_mapping VALUES (?, ?)", (chat_id, stream["original_video_id"]))
        conn.commit()
        conn.close()

    return url

def delete_clip(clip_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT video, message_id FROM messages WHERE clip_id=?", (clip_id,))
    row = cur.fetchone()
    conn.close()

    if row:
        video_id, message_id = row
        success = delete_discord_message(video_id, message_id)
        return "✅ Clip deleted." if success else "⚠️ Failed to delete clip."
    return "⚠️ Clip not found."
