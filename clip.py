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

    return f"Streamclipper successfully created clip [{clip_id}] — '{title}' by {user.name}, with a delay of {delay} seconds. The clip was successfully sent to Discord." if success else "✅ Clip created, but failed to notify Discord."


def delete_clip(clip_id):
    conn = sqlite3.connect("queries.db")
    cur = conn.cursor()

    cur.execute("CREATE TABLE IF NOT EXISTS settings (channel TEXT PRIMARY KEY, webhook TEXT)")

    # looking for channel id and webhook from db
    cur.execute("SELECT channel, webhook FROM settings WHERE channel=?", (clip_id,))
    row = cur.fetchone()
    if not row:
        return f"❌ Clip {clip_id} not found."

    channel_id, webhook_url = row

    #deletion in db with the help of clip id
    try:
        cur.execute(
            "DELETE FROM QUERIES WHERE channel_id=? AND message_id LIKE ?",
            (channel_id, f"%{clip_id[:3]}"),
        )
        conn.commit()
    except Exception as e:
        print(f"❌ Error during DB deletion: {e}")
        conn.close()
        return f"❌ Error during deletion process."

    #attempting to delete msg if webhook url is there
    if webhook_url:
        try:
            webhook = DiscordWebhook(
                url=webhook_url,
                id=clip_id,
                allowed_mentions={"role": [], "user": [], "everyone": False}
            )
            webhook.delete()  # Delete the Discord webhook message
        except Exception as e:
            print(f"❌ Error deleting Discord webhook: {e}")

    conn.close()
    return f"✅ Clip {clip_id} deleted successfully."
