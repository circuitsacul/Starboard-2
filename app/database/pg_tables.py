GUILDS = \
    """CREATE TABLE IF NOT EXISTS guilds (
        id NUMERIC PRIMARY KEY,

        log_channel NUMERIC DEFAULT NULL,
        level_channel NUMERIC DEFAULT NULL,
        ping_user BOOL NOT NULL DEFAULT false,

        premium_end TIMESTAMP DEFAULT NULL,

        prefixes TEXT[] NOT NULL DEFAULT '{"sb!"}'
    )"""

USERS = \
    """CREATE TABLE IF NOT EXISTS users (
        id NUMERIC PRIMARY KEY
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
        self_star BOOL NOT NULL DEFAULT False,
        unstar BOOL NOT NULL DEFAULT False,
        allow_bots BOOL NOT NULL DEFAULT True,
        link_deletes BOOL NOT NULL DEFAULT False,
        link_edits BOOL NOT NULL DEFAULT True,
        images_only BOOL NOT NULL DEFAULT False,
        remove_invalid BOOL NOT NULL DEFAULT True,
        no_xp BOOL NOT NULL DEFAULT False,

        star_emojis TEXT[] DEFAULT '{⭐}',
        display_emoji TEXT DEFAULT '⭐',

        FOREIGN KEY (guild_id) REFERENCES guilds (id)
            ON DELETE CASCADE
    )"""

SETTING_OVERRIDES = \
    """CREATE TABLE IF NOT EXISTS setting_overrides (
        id BIGINT PRIMARY KEY,
        name VARCHAR(32) NOT NULL,

        starboards NUMERIC[] NOT NULL,
        channel_mode SMALLINT NOT NULL DEFAULT 0,
        channels NUMERIC[] DEFAULT NULL,

        has_any_role NUMERIC[] DEFAULT NULL,
        has_all_roles NUMERIC[] DEFAULT NULL,
        lacks_any_role NUMERIC[] DEFAULT NULL,
        lacks_all_roles NUMERIC[] DEFAULT NULL,

        required SMALLINT DEFAULT NULL,
        required_remove SMALLINT DEFAULT NULL,
        self_star BOOL DEFAULT NULL,
        unstar BOOL DEFAULT NULL,
        allow_bots BOOL DEFAULT NULL,
        link_deletes BOOL DEFAULT NULL,
        link_edits BOOL DEFAULT NULL,
        images_only BOOL DEFAULT NULL,
        remove_invalid BOOL DEFAULT NULL,
        no_xp BOOL DEFAULT NULL,

        star BOOL DEFAULT NULL,
        recv_star BOOL DEFAULT NULL,

        allow_command BOOL DEFAULT NULL,
        qa BOOL DEFAULT NULL
    )"""

MESSAGES = \
    """CREATE TABLE IF NOT EXISTS messages (
        id NUMERIC PRIMARY KEY,
        guild_id NUMERIC NOT NULL,
        channel_id NUMERIC NOT NULL,
        author_id NUMERIC,

        points SMALLINT DEFAULT NULL,

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

        FOREIGN KEY (orig_id) REFERENCES messages (id)
            ON DELETE CASCADE,
        FOREIGN KEY (starboard_id) REFERENCES starboards (id)
            ON DELETE CASCADE
    )"""

REACTIONS = \
    """CREATE TABLE IF NOT EXISTS reactions (
        id BIGINT PRIMARY KEY,
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
            ON DELETE SET NULL
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
