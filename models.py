class User:
    def __init__(self, provider_id, display_name, user_level):
        self.id = provider_id
        self.name = display_name
        self.level = user_level
        self.avatar = None
