import time
from util import (
    get_user_details_from_headers,
    get_stream_metadata,
    seconds_to_hms,
    send_discord_webhook
)
from models import User

def create_clip(chat_id, query, headers):
    user = get_user_details_from_headers(headers)
    channel_id = user.id[:24]

    metadata = get_stream_metadata(channel_id, chat_id)
    if not metadata or "start_time" not in metadata:
        return "❌ Unable to locate active live stream."

    timestamp_usec = int(headers.get("Nightbot-Message-Timestamp", "0"))
    if not timestamp_usec:
        timestamp_usec = int(time.time() * 1_000_000)

    delay = int(headers.get("delay", "-30"))
    stream_start = int(metadata["start_time"])
    video_id = metadata.get("original_video_id") or metadata.get("video_id")
    clip_time = (timestamp_usec - stream_start) // 1_000_000 + delay
    hms = seconds_to_hms(clip_time)
    clip_id = chat_id[-3:].upper() + str(timestamp_usec % 100000)
    title = query.replace("+", " ") if query else "Untitled"
    url = f"<https://youtu.be/{video_id}?t={clip_time}>"

    success = send_discord_webhook(clip_id, title, hms, url, delay, user, channel_id)

    return f"Clipped {clip_id} - by {user.name}, Sent to discord" if success else "✅ Clip created, but failed to notify Discord."

def delete_clip(clip_id):
    import sqlite3
    import requests
    conn = sqlite3.connect("data/queries.db")
    cur = conn.cursor()
    cur.execute("SELECT channel FROM chat_mapping WHERE chat LIKE ?", (f"%{clip_id[:3]}%",))
    row = cur.fetchone()
    conn.close()

    if not row:
        return "❌ Clip not found in database."

    webhook = None
    conn = sqlite3.connect("data/queries.db")
    cur = conn.cursor()
    cur.execute("SELECT webhook FROM settings WHERE channel=?", (row[0],))
    row2 = cur.fetchone()
    conn.close()

    if not row2:
        return "❌ Webhook not found."

    webhook = row2[0]

    try:
        r = requests.get(webhook)
        if r.ok:
            messages = r.json()
            for msg in messages:
                if clip_id in msg.get("content", ""):
                    del_url = f"{webhook}/messages/{msg['id']}"
                    requests.delete(del_url)
                    return f"🗑️ Deleted message {msg['id']}"
    except Exception as e:
        return f"❌ Delete error: {e}"

    return "❌ Clip not found in messages."
