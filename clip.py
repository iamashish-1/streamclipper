from util import get_stream_metadata, hms, send_discord_webhook, delete_from_discord
from models import User, Channel
import time


def create_clip(chat_id, query, headers):
    user = User(headers)
    channel_id = chat_id[:24]
    channel = Channel(channel_id, "data/queries.db")

    stream = get_stream_metadata(channel_id, chat_id)
    if not stream:
        return "⚠️ No valid live video found."

    now = time.time()
    start_us = stream.get("start_time", int((now - 3600) * 1_000_000))
    delay = int(float(headers.get("delay", "-30")))
    offset = int(now - delay - (start_us / 1_000_000))
    video_id = stream["original_video_id"]

    clip_id = chat_id[-3:].upper() + str(int(now))[-5:]
    title = query.replace("+", " ") if query else "Untitled"
    url = f"https://youtu.be/{video_id}?t={offset}"
    hms_time = hms(offset)

    print(f"⏱️ Generating clip at {hms_time} from video {video_id}")
    sent = send_discord_webhook(clip_id, title, hms_time, url, delay, user, channel)
    return url if sent else f"{url} (but webhook failed)"


def delete_clip(clip_id):
    success = delete_from_discord(clip_id)
    return f"🗑️ Deleted {clip_id}" if success else "❌ Delete failed"
