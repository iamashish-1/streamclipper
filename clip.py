import time

from util import (
    get_user_details_from_headers,
    get_stream_metadata,
    seconds_to_hms,
    send_discord_webhook
)
import sqlite3
from discord_webhook import DiscordWebhook

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

    return f"Streamclipper successfully created clip [{clip_id}] — '{title}' by @{user.name}, with a delay of {delay} seconds. The clip was successfully sent to Discord." if success else "✅ Clip created, but failed to notify Discord."


def delete_clip(clip_id):
    conn = sqlite3.connect("queries.db")
    cur = conn.cursor()

    # Find the clip in the database based on ID suffix and timestamp window
    cur.execute("""
        SELECT channel_id, message_id, time_in_seconds, webhook
        FROM queries
        WHERE message_id LIKE ?
    """, (f"%{clip_id[:3]}",))

    clip = cur.fetchone()

    if not clip:
        conn.close()
        return f"❌ Clip {clip_id} not found."

    channel_id, message_id, clip_time, webhook_id = clip

    # Delete from database using precise match
    cur.execute("""
        DELETE FROM queries
        WHERE channel_id = ? AND message_id LIKE ? AND time_in_seconds BETWEEN ? AND ?
    """, (
        channel_id,
        f"%{clip_id[:3]}",
        clip_time - 1,
        clip_time + 1
    ))
    conn.commit()

    # Get the webhook URL from settings
    cur.execute("SELECT webhook FROM settings WHERE channel = ?", (channel_id,))
    row = cur.fetchone()
    conn.close()

    if row and webhook_id:
        try:
            from discord_webhook import DiscordWebhook
            webhook_url = row[0]
            webhook = DiscordWebhook(
                url=webhook_url,
                id=webhook_id,
                allowed_mentions={"role": [], "user": [], "everyone": False}
            )
            webhook.delete()
        except Exception as e:
            print(f"❌ Failed to delete webhook message: {e}")

    return f"✅ Clip {clip_id} deleted successfully."

