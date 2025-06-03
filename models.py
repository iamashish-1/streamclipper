class User:
    def __init__(self, header):
        from urllib.parse import parse_qs
        parsed = parse_qs(header)
        self.name = parsed.get("displayName", ["Unknown"])[0].replace("+", " ")
        self.level = parsed.get("userLevel", [""])[0].lower()
        self.id = parsed.get("providerId", [""])[0]

class Channel:
    def __init__(self, channel_id, webhook=None):
        self.id = channel_id
        self.webhook = webhook
