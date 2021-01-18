GUILDS = \
    """CREATE TABLE IF NOT EXISTS guilds (
        id NUMERIC PRIMARY KEY,

        log_channel NUMERIC DEFAULT NULL,
        level_channel NUMERIC DEFAULT NULL,
        ping_user BOOL NOT NULL DEFAULT false,

        allow_commands BOOL NOT NULL DEFAULT true,

        premium_end TIMESTAMP DEFAULT NULL,

        prefixes VARCHAR(8)[] NOT NULL DEFAULT '{"sb!"}'
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

        star_emojis TEXT[] DEFAULT '{⭐}',
        display_emoji TEXT DEFAULT '⭐',

        FOREIGN KEY (guild_id) REFERENCES guilds (id)
            ON DELETE CASCADE
    )"""

SETTING_OVERRIDES = \
    """CREATE TABLE IF NOT EXISTS setting_overrides (
        id SERIAL PRIMARY KEY,
        guild_id NUMERIC NOT NULL,
        index SMALLINT NOT NULL,
        name VARCHAR(32) NOT NULL,

        starboards NUMERIC[] NOT NULL,
        in_channels NUMERIC[] DEFAULT '{}',
        not_in_channels NUMERIC[] DEFAULT '{}',

        has_roles NUMERIC[] DEFAULT '{}',
        lacks_roles NUMERIC[] DEFAULT '{}',

        required SMALLINT DEFAULT NULL,
        required_remove SMALLINT DEFAULT NULL,
        self_star BOOL DEFAULT NULL,
        allow_bots BOOL DEFAULT NULL,
        allow_nsfw BOOL DEFAULT NULL,
        link_deletes BOOL DEFAULT NULL,
        link_edits BOOL DEFAULT NULL,
        images_only BOOL DEFAULT NULL,
        remove_reactions BOOL DEFAULT NULL,
        no_xp BOOL DEFAULT NULL,
        explore BOOL DEFAULT NULL,

        star BOOL DEFAULT NULL,
        recv_star BOOL DEFAULT NULL,
        gain_xp_roles BOOL DEFAULT NULL,
        gain_pos_roles BOOL DEFAULT NULL,

        allow_commands BOOL DEFAULT NULL,
        qa BOOL DEFAULT NULL,

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
    SETTING_OVERRIDES,
    MESSAGES,
    STARBOARD_MESSAGES,
    REACTIONS,
    REACTION_USERS
]
