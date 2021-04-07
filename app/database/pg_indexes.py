MEMBERS__USER_ID__GUILD_ID = """CREATE INDEX IF NOT EXISTS
    members__user_id ON members (user_id, guild_id)"""

ALL_INDEXES = [MEMBERS__USER_ID__GUILD_ID]
