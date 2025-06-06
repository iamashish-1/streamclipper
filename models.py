class User:
    def __init__(self, headers):
        from urllib.parse import parse_qs
        raw = headers.get("Nightbot-User", "")
        parts = parse_qs(raw)
        self.id = parts.get("providerId", [""])[0]
        self.name = parts.get("displayName", ["Unknown"])[0].replace("+", " ")
        self.level = parts.get("userLevel", [""])[0].lower()
        self.avatar = None

    def __str__(self):
        return f"{self.name} ({self.level})"


class Channel:
    def __init__(self, channel_id, db_path):
        import sqlite3
        self.id = channel_id
        self.webhook = None

        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT webhook FROM settings WHERE channel=?", (channel_id,))
        row = cur.fetchone()
        conn.close()
        if row:
            self.webhook = row[0]
