CREATE INDEX IF NOT EXISTS
    members__user_id__guild_id ON members (user_id, guild_id);

CREATE INDEX IF NOT EXISTS
    starboards__guild_id ON starboards USING HASH (guild_id);

CREATE UNIQUE INDEX IF NOT EXISTS
    reaction_users__reaction_id__user_id ON reaction_users
    (reaction_id, user_id);

CREATE INDEX IF NOT EXISTS
    starboard_messages__starboard_id ON starboard_messages
    USING HASH (starboard_id);

CREATE INDEX IF NOT EXISTS
    members_posroles__user_id ON members_posroles
    USING HASH (user_id);

CREATE INDEX IF NOT EXISTS
    members_posroles__guild_id ON members_posroles
    USING HASH (guild_id);