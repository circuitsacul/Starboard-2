MEMBERS__USER_ID__GUILD_ID = """CREATE INDEX IF NOT EXISTS
    members__user_id__guild_id ON members (user_id, guild_id)"""

STARBOARDS__GUILD_ID = """CREATE INDEX IF NOT EXISTS
    starboards__guild_id ON starboards USING HASH (guild_id)"""

REACTION_USERS__REACTION_ID__USER_ID = """CREATE UNIQUE INDEX IF NOT EXISTS
    reaction_users__reaction_id__user_id ON reaction_users
    (reaction_id, user_id)"""

STARBOARD_MESSAGES__STARBOARD_ID = """CREATE INDEX IF NOT EXISTS
    starboard_messages__starboard_id ON starboard_messages
    USING HASH (starboard_id)"""

MEMBERS_POSROLES__ROLE_ID = """CREATE INDEX IF NOT EXISTS
    members_posroles__role_id ON members_posroles
    USING HASH (role_id)"""

MEMBERS_POSROLES__USER_ID = """CREATE INDEX IF NOT EXISTS
    members_posroles__user_id ON members_posroles
    USING HASH (user_id)"""

MEMBERS_POSROLES__GUILD_ID = """CREATE INDEX IF NOT EXISTS
    members_posroles__guild_id ON members_posroles
    USING HASH (guild_id)"""

ALL_INDEXES = [
    MEMBERS__USER_ID__GUILD_ID,
    STARBOARDS__GUILD_ID,
    REACTION_USERS__REACTION_ID__USER_ID,
    STARBOARD_MESSAGES__STARBOARD_ID,
    MEMBERS_POSROLES__USER_ID,
    MEMBERS_POSROLES__ROLE_ID,
    MEMBERS_POSROLES__GUILD_ID,
]
