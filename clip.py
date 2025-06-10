import time
import sqlite3
from util import (
    get_user_details_from_headers,
    get_stream_metadata,
    seconds_to_hms,
    send_discord_webhook, DB_PATH
)
from discord_webhook import DiscordWebhook

#-- Creating clip and clip information
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

    success = send_discord_webhook(clip_id, title, hms, url, delay, user, channel_id, video_id)
    print("Clip successfully sent to Discord!")
    return f"Streamclipper successfully created clip [{clip_id}] — '{title}' by @{user.name}, with a delay of {delay} seconds. The clip was successfully sent to Discord." if success else "✅ Clip created, but failed to notify Discord."

#-- Function to delete clip from discord and database
def delete_clip(clip_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    clip_id = clip_id.upper()
    cur.execute("SELECT channel, message_id FROM clips WHERE clip_id=?", (clip_id,))
    result = cur.fetchone()
    print("🔍 Clip fetch result:", result)


    if not result:
        return f"❌ Clip {clip_id} not found."

    channel, message_id = result

    cur.execute("SELECT webhook FROM settings WHERE channel=?", (channel,))
    row = cur.fetchone()
    if not row:
        return f"⚠️ Webhook not found for channel {channel}."

    webhook_url = row[0]

    try:
        webhook = DiscordWebhook(url=webhook_url, id=message_id)
        webhook.delete()
        print(f"🗑️ Deleted Discord message: {message_id}")
    except Exception as e:
        print(f"⚠️ Failed to delete Discord message: {e}")

    cur.execute("DELETE FROM clips WHERE clip_id=?", (clip_id,))
    print("Deleted clip from database and Discord!")
    conn.commit()
    conn.close()

    return f"Streamclipper deleted clip with ID - '{clip_id}'"

