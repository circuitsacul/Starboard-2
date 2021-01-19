GUILDS = \
    """CREATE TABLE IF NOT EXISTS guilds (
        id NUMERIC PRIMARY KEY,

        log_channel NUMERIC DEFAULT NULL,
        level_channel NUMERIC DEFAULT NULL,
        ping_user BOOL NOT NULL DEFAULT false,

        allow_commands BOOL NOT NULL DEFAULT true,

        premium_end TIMESTAMP DEFAULT NULL,

        qa_enabled BOOL NOT NULL DEFAULT true,
        qa_force TEXT NOT NULL DEFAULT '🔒',
        qa_unforce TEXT NOT NULL DEFAULT '🔓',
        qa_trash TEXT NOT NULL DEFAULT '🗑️',
        qa_recount TEXT NOT NULL DEFAULT '🔃',
        qa_save TEXT NOT NULL DEFAULT '📥',

        prefixes VARCHAR(8)[] NOT NULL DEFAULT '{"sb!"}',

        xp_cooldown_time SMALLINT DEFAULT 3,
        xp_cooldown_per SMALLINT DEFAULT 60
    )"""

USERS = \
    """CREATE TABLE IF NOT EXISTS users (
        id NUMERIC PRIMARY KEY,
        is_bot BOOL NOT NULL,
        votes SMALLINT NOT NULL DEFAULT 0
    )"""

MEMBERS = \
    """CREATE TABLE IF NOT EXISTS members (
        user_id NUMERIC NOT NULL,
        guild_id NUMERIC NOT NULL,

        stars_given SMALLINT NOT NULL DEFAULT 0,
        stars_received SMALLINT NOT NULL DEFAULT 0,

        xp SMALLINT NOT NULL DEFAULT 0,
        level SMALLINT NOT NULL DEFAULT 0,

        roles NUMERIC [] NOT NULL DEFAULT '{}',

        FOREIGN KEY (user_id) REFERENCES users (id)
            ON DELETE CASCADE,
        FOREIGN KEY (guild_id) REFERENCES guilds (id)
            ON DELETE CASCADE
    )"""

STARBOARDS = \
    """CREATE TABLE IF NOT EXISTS starboards (
        id NUMERIC PRIMARY KEY,
        guild_id NUMERIC NOT NULL,

        required SMALLINT NOT NULL DEFAULT 3,
        required_remove SMALLINT NOT NULL DEFAULT 0,
        autoreact BOOL NOT NULL DEFAULT True,
        self_star BOOL NOT NULL DEFAULT False,
        allow_bots BOOL NOT NULL DEFAULT True,
        allow_nsfw BOOL NOT NULL DEFAULT False,
        link_deletes BOOL NOT NULL DEFAULT False,
        link_edits BOOL NOT NULL DEFAULT True,
        images_only BOOL NOT NULL DEFAULT False,
        remove_reactions BOOL NOT NULL DEFAULT True,
        no_xp BOOL NOT NULL DEFAULT False,
        explore BOOL NOT NULL DEFAULT True,

        require_regex TEXT DEFAULT NULL,
        exclude_regex TEXT DEFAULT NULL,

        star_emojis TEXT[] DEFAULT '{⭐}',
        display_emoji TEXT DEFAULT '⭐',

        FOREIGN KEY (guild_id) REFERENCES guilds (id)
            ON DELETE CASCADE
    )"""

PERMROLES = \
    """CREATE TABLE IF NOT EXISTS permroles (
        guild_id NUMERIC NOT NULL,
        role_id NUMERIC NOT NULL,
        index SMALLINT NOT NULL,

        starboards NUMERIC[] DEFAULT '{}',
        channels NUMERIC[] DEFAULT '{}',

        allow_commands BOOL DEFAULT NULL,
        recv_stars BOOL DEFAULT NULL,
        give_stars BOOL DEFAULT NULL,
        gain_xp BOOL DEFAULT NULL,
        pos_roles BOOL DEFAULT NULL,
        xp_roles BOOL DEFAULT NULL,
        overrides BOOL DEFAULT NULL

        FOREIGN KEY (guild_id) REFERENCES guilds (id)
            ON DELETE CASCADE
    )"""

MESSAGES = \
    """CREATE TABLE IF NOT EXISTS messages (
        id NUMERIC PRIMARY KEY,
        guild_id NUMERIC NOT NULL,
        channel_id NUMERIC NOT NULL,
        author_id NUMERIC,

        is_nsfw BOOL NOT NULL,

        forced NUMERIC[] NOT NULL DEFAULT '{}',
        trashed BOOL NOT NULL DEFAULT false,

        FOREIGN KEY (guild_id) REFERENCES guilds (id)
            ON DELETE CASCADE,
        FOREIGN KEY (author_id) REFERENCES users (id)
            ON DELETE SET NULL
    )"""

STARBOARD_MESSAGES = \
    """CREATE TABLE IF NOT EXISTS starboard_messages (
        id NUMERIC PRIMARY KEY,
        orig_id NUMERIC NOT NULL,
        starboard_id NUMERIC NOT NULL,

        points SMALLINT NOT NULL DEFAULT 0,

        FOREIGN KEY (orig_id) REFERENCES messages (id)
            ON DELETE CASCADE,
        FOREIGN KEY (starboard_id) REFERENCES starboards (id)
            ON DELETE CASCADE
    )"""

REACTIONS = \
    """CREATE TABLE IF NOT EXISTS reactions (
        id SERIAL PRIMARY KEY,
        emoji TEXT NOT NULL,
        message_id NUMERIC NOT NULL,

        FOREIGN KEY (message_id) REFERENCES messages (id)
            ON DELETE CASCADE
    )"""

REACTION_USERS = \
    """CREATE TABLE IF NOT EXISTS reaction_users (
        reaction_id BIGINT NOT NULL,
        user_id NUMERIC NOT NULL,

        FOREIGN KEY (reaction_id) REFERENCES reactions (id)
            ON DELETE CASCADE,
        FOREIGN KEY (user_id) REFERENCES users (id)
            ON DELETE CASCADE
    )"""

ALL_TABLES = [
    GUILDS,
    USERS,
    MEMBERS,
    STARBOARDS,
    PERMROLES,
    MESSAGES,
    STARBOARD_MESSAGES,
    REACTIONS,
    REACTION_USERS
]
