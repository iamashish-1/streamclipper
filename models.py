import sqlite3
from urllib.parse import parse_qs

DB_PATH = "data/queries.db"

class User:
    def __init__(self, headers):
        raw = headers.get("Nightbot-User", "")
        parsed = parse_qs(raw)
        self.name = parsed.get("displayName", ["Unknown"])[0].replace("+", " ")
        self.level = parsed.get("userLevel", [""])[0].lower()
        self.id = parsed.get("providerId", [""])[0]

class Channel:
    def __init__(self, channel_id, db_path=DB_PATH):
        self.channel_id = channel_id
        self.db_path = db_path

    def get_webhook(self):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT webhook FROM settings WHERE channel=?", (self.channel_id,))
        row = cur.fetchone()
        conn.close()
        return row[0] if row else None
