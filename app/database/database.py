import time
from typing import Any, List, Optional

import asyncpg
import discord

from .. import errors
from .pg_tables import ALL_TABLES


class Database:
    def __init__(self, database: str, user: str, password: str) -> None:
        self.name = database
        self.user = user
        self.password = password

        self.pool: asyncpg.pool.Pool = None

        self.sql_times: dict = {}

    def log(self, sql: str, time: float) -> None:
        self.sql_times.setdefault(sql, [])
        self.sql_times[sql].append(time)

    async def init_database(self) -> None:
        self.pool = await asyncpg.create_pool(
            database=self.name, user=self.user, password=self.password
        )

        async with self.pool.acquire() as con:
            async with con.transaction():
                for table in ALL_TABLES:
                    await con.execute(table)

    async def execute(self, sql: str, *args: list) -> None:
        async with self.pool.acquire() as con:
            async with con.transaction():
                s = time.time()
                await con.execute(sql, *args)
        self.log(sql, time.time() - s)

    async def fetch(self, sql: str, *args: list) -> List[dict]:
        async with self.pool.acquire() as con:
            async with con.transaction():
                s = time.time()
                result = await con.fetch(sql, *args)
        self.log(sql, time.time() - s)
        return result

    async def fetchrow(self, sql: str, *args: list) -> Optional[dict]:
        async with self.pool.acquire() as con:
            async with con.transaction():
                s = time.time()
                result = await con.fetchrow(sql, *args)
        self.log(sql, time.time() - s)
        return result

    async def fetchval(self, sql: str, *args: list) -> Optional[Any]:
        async with self.pool.acquire() as con:
            async with con.transaction():
                s = time.time()
                result = await con.fetchval(sql, *args)
        self.log(sql, time.time() - s)
        return result

    async def get_guild(self, guild_id: int) -> Optional[dict]:
        sql_guild = await self.fetchrow(
            """SELECT * FROM guilds
            WHERE id=$1""",
            guild_id,
        )
        return sql_guild

    async def create_guild(
        self, guild_id: int, check_first: bool = True
    ) -> bool:
        if check_first:
            exists = await self.get_guild(guild_id) is not None
            if exists:
                return False

        try:
            await self.execute(
                """INSERT INTO guilds (id)
                VALUES ($1)""",
                guild_id,
            )
        except asyncpg.exceptions.UniqueViolationError:
            return False
        return True

    async def get_user(self, user_id: int) -> Optional[dict]:
        return await self.fetchrow(
            """SELECT * FROM users
            WHERE id=$1""",
            user_id,
        )

    async def create_user(
        self, user_id: int, is_bot: bool, check_first: bool = True
    ) -> None:
        if check_first:
            exists = await self.get_user(user_id) is not None
            if exists:
                return True

        try:
            await self.execute(
                """INSERT INTO users (id, is_bot)
                VALUES ($1, $2)""",
                user_id,
                is_bot,
            )
        except asyncpg.exceptions.UniqueViolationError:
            return True
        return False

    async def get_member(self, user_id: int, guild_id: int) -> Optional[dict]:
        return await self.fetchrow(
            """SELECT * FROM members
            WHERE user_id=$1 AND guild_id=$2""",
            user_id,
            guild_id,
        )

    async def create_member(
        self, user_id: int, guild_id: int, check_first: bool = True
    ) -> None:
        if check_first:
            exists = await self.get_member(user_id, guild_id) is not None
            if exists:
                return True

        await self.create_guild(guild_id)
        try:
            await self.execute(
                """INSERT INTO members (user_id, guild_id)
                VALUES ($1, $2)""",
                user_id,
                guild_id,
            )
        except asyncpg.exceptions.UniqueViolationError:
            return True
        return False

    async def get_starboard(self, starboard_id: int) -> Optional[dict]:
        return await self.fetchrow(
            """SELECT * FROM starboards
            WHERE id=$1""",
            starboard_id,
        )

    async def get_starboards(self, guild_id: int) -> List[dict]:
        return await self.fetch(
            """SELECT * FROM starboards
            WHERE guild_id=$1""",
            guild_id,
        )

    async def create_starboard(
        self, channel_id: int, guild_id: int, check_first: bool = True
    ) -> None:
        if check_first:
            exists = await self.get_starboard(channel_id) is not None
            if exists:
                return True

        await self.create_guild(guild_id)
        try:
            await self.execute(
                """INSERT INTO starboards (id, guild_id)
                VALUES ($1, $2)""",
                channel_id,
                guild_id,
            )
        except asyncpg.exceptions.UniqueViolationError:
            return True
        return False

    async def edit_starboard(
        self,
        starboard_id: int = None,
        required: int = None,
        required_remove: int = None,
        autoreact: bool = None,
        self_star: bool = None,
        allow_bots: bool = None,
        allow_nsfw: bool = None,
        link_deletes: bool = None,
        link_edits: bool = None,
        images_only: bool = None,
        remove_reactions: bool = None,
        no_xp: bool = None,
        explore: bool = None,
        star_emojis: List[str] = None,
        display_emoji: str = None,
        regex: str = None,
        exclude_regex: str = None,
        color: int = None,
    ) -> None:
        s = await self.get_starboard(starboard_id)
        if not s:
            raise errors.DoesNotExist(
                f"Starboard {starboard_id} does not exist."
            )

        settings = {
            "required": s["required"] if required is None else required,
            "required_remove": s['required_remove'] if required_remove
            is None else required_remove,
            "autoreact": s['autoreact'] if autoreact is None else autoreact,
            "self_star": s['self_star'] if self_star is None else self_star,
            "allow_bots": s['allow_bots'] if allow_bots is None else
            allow_bots,
            "allow_nsfw": s['allow_nsfw'] if allow_nsfw is None else
            allow_nsfw,
            "link_deletes": s['link_deletes'] if link_deletes is None else
            link_deletes,
            "link_edits": s['link_edits'] if link_edits is None else
            link_edits,
            "images_only": s['images_only'] if images_only is None else
            images_only,
            "remove_reactions": s['remove_reactions'] if remove_reactions is
            None else remove_reactions,
            "no_xp": s['no_xp'] if no_xp is None else no_xp,
            "explore": s['explore'] if explore is None else explore,
            "star_emojis": s['star_emojis'] if star_emojis is None else
            star_emojis,
            "display_emoji": s['display_emoji'] if display_emoji is None else
            display_emoji,
            "regex": s['regex'] if regex is None else regex,
            "exclude_regex": s['exclude_regex'] if exclude_regex is None else
            exclude_regex,
            "color": s["color"] if color is None else color
        }

        if settings['required'] <= settings['required_remove']:
            raise discord.InvalidArgument(
                "requiredStars cannot be less than or equal to "
                "requiredToRemove"
            )
        if settings['required'] < 1:
            raise discord.InvalidArgument(
                "requiredStars cannot be less than 1"
            )
        if settings['required'] > 500:
            raise discord.InvalidArgument(
                "requiredStars cannot be greater than 500"
            )
        if settings['required_remove'] < -1:
            raise discord.InvalidArgument(
                "requiredToRemove cannot be less than -1"
            )
        if settings['required_remove'] > 495:
            raise discord.InvalidArgument(
                "requiredToRemove cannot be greater tahn 495"
            )

        await self.execute(
            """UPDATE starboards
            SET required = $1,
            required_remove = $2,
            autoreact = $3,
            self_star = $4,
            allow_bots = $5,
            allow_nsfw = $6,
            link_deletes = $7,
            link_edits = $8,
            images_only = $9,
            remove_reactions = $10,
            no_xp = $11,
            explore = $12,
            star_emojis = $13,
            display_emoji = $14,
            regex = $15,
            exclude_regex = $16,
            color = $17
            WHERE id = $18""",
            settings['required'],
            settings['required_remove'],
            settings['autoreact'],
            settings['self_star'],
            settings['allow_bots'],
            settings['allow_nsfw'],
            settings['link_deletes'],
            settings['link_edits'],
            settings['images_only'],
            settings['remove_reactions'],
            settings['no_xp'],
            settings['explore'],
            settings['star_emojis'],
            settings['display_emoji'],
            settings['regex'],
            settings['exclude_regex'],
            settings['color'],
            starboard_id,
        )

    async def add_star_emoji(self, starboard_id: int, emoji: str) -> None:
        if type(emoji) is not str:
            raise ValueError("Expected a str for emoji")

        starboard = await self.get_starboard(starboard_id)
        if emoji in starboard["star_emojis"]:
            raise errors.AlreadyExists(
                f"{emoji} is already a starEmoji on " f"{starboard['id']}"
            )

        await self.edit_starboard(
            starboard_id, star_emojis=starboard["star_emojis"] + [emoji]
        )

    async def remove_star_emoji(self, starboard_id: int, emoji: str) -> None:
        if type(emoji) is not str:
            raise ValueError("Expected a str for emoji")

        starboard = await self.get_starboard(starboard_id)
        if emoji not in starboard["star_emojis"]:
            raise errors.DoesNotExist(
                f"{emoji} is already a starEmoji on " f"{starboard['id']}"
            )

        new_emojis = starboard["star_emojis"]
        new_emojis.remove(emoji)

        await self.edit_starboard(starboard_id, star_emojis=new_emojis)

    #    async def get_setting_overrides(
    #        self,
    #        starboard: int = [],
    #        channel: int = [],
    #        roles: List[int] = []
    #    ) -> Optional[dict]:
    #        setting_overrides = await self.fetch(
    #            """SELECT * FROM setting_overrides
    #            WHERE $1::numeric = any(starboards)
    #            AND in_channels = '{}' or $2::numeric = any(in_channels)
    #            AND not_in_channels = '{}' or $2::numeric != all (not_in_channels)
    #            AND (EXISTS(
    #                    (SELECT $3::numeric[])
    #                    INTERSECT
    #                    SELECT has_roles
    #                ))
    #            AND (NOT EXISTS(
    #                    (SELECT $3::numeric[])
    #                    INTERSECT
    #                    SELECT lacks_roles
    #                ))
    #            ORDER BY index DESC;
    #            """, starboard, channel, roles
    #        )
    #        return setting_overrides

    async def get_message(self, message_id: int) -> dict:
        return await self.fetchrow(
            """SELECT * FROM messages
            WHERE id=$1""",
            message_id,
        )

    async def create_message(
        self,
        message_id: int,
        guild_id: int,
        channel_id: int,
        author_id: int,
        is_nsfw: bool,
        check_first: bool = True,
    ) -> bool:
        if check_first:
            exists = await self.get_message(message_id) is not None
            if exists:
                return True

        is_starboard_message = (
            await self.get_starboard_message(message_id) is not None
        )
        if is_starboard_message:
            raise errors.AlreadyStarboardMessage(
                f"Could not create message {message_id} "
                "because it is already starboard message."
            )

        await self.create_guild(guild_id)

        try:
            await self.execute(
                """INSERT INTO messages
                (id, guild_id, channel_id, author_id, is_nsfw)
                VALUES ($1, $2, $3, $4, $5)""",
                message_id,
                guild_id,
                channel_id,
                author_id,
                is_nsfw,
            )
        except asyncpg.exceptions.UniqueViolationError:
            return True
        return False

    async def get_starboard_message(self, message_id: int) -> Optional[dict]:
        return await self.fetchrow(
            """SELECT * FROM starboard_messages
            WHERE id=$1""",
            message_id,
        )

    async def get_starboard_messages(self, orig_id: int) -> List[dict]:
        return await self.fetch(
            """SELECT * FROM starboard_messages
            WHERE orig_id=$1"""
        )

    async def get_starboard_message_from_starboard(
        self, orig_id: int, starboard_id: int
    ) -> Optional[dict]:
        return await self.fetchrow(
            """SELECT * FROM starboard_messages
            WHERE orig_id=$1 AND starboard_id=$2""",
            orig_id,
            starboard_id,
        )

    async def create_starboard_message(
        self,
        message_id: int,
        orig_id: int,
        starboard_id: int,
        check_first: bool = True,
    ) -> bool:
        if check_first:
            exists = await self.get_starboard_message(message_id)
            if exists:
                return True

        already_orig_message = await self.get_message(message_id) is not None
        if already_orig_message:
            raise errors.AlreadyOrigMessage(
                f"Could not create starboard message {message_id} "
                "because it is already a normal message."
            )

        try:
            await self.execute(
                """INSERT INTO starboard_messages
                (id, orig_id, starboard_id)
                VALUES ($1, $2, $3)""",
                message_id,
                orig_id,
                starboard_id,
            )
        except asyncpg.exceptions.UniqueViolationError:
            return True
        return False

    async def get_reaction(
        self, emoji: str, message_id: int
    ) -> Optional[dict]:
        return await self.fetchrow(
            """SELECT * FROM reactions
            WHERE emoji=$1 AND message_id=$2""",
            emoji,
            message_id,
        )

    async def create_reaction(
        self, emoji: str, message_id: int, check_first: bool = True
    ) -> bool:
        if check_first:
            exists = await self.get_reaction(emoji, message_id)
            if exists:
                return True

        try:
            await self.execute(
                """INSERT INTO reactions
                (emoji, message_id)
                VALUES ($1, $2)""",
                emoji,
                message_id,
            )
        except asyncpg.exceptions.UniqueViolationError:
            return True
        return False

    async def get_reaction_user(
        self, emoji: str, message_id: int, user_id: int
    ) -> Optional[dict]:
        reaction = await self.get_reaction(emoji, message_id)
        if reaction is None:
            return None
        return await self.fetchrow(
            """SELECT * FROM reaction_users
            WHERE reaction_id=$1 AND user_id=$2""",
            reaction["id"],
            user_id,
        )

    async def create_reaction_user(
        self,
        emoji: str,
        message_id: int,
        user_id: int,
        check_first: bool = True,
    ) -> bool:
        if check_first:
            exists = await self.get_reaction_user(emoji, message_id, user_id)
            if exists:
                return True

        await self.create_reaction(emoji, message_id)

        reaction = await self.get_reaction(emoji, message_id)

        try:
            await self.execute(
                """INSERT INTO reaction_users
                (reaction_id, user_id)
                VALUES ($1, $2)""",
                reaction["id"],
                user_id,
            )
        except asyncpg.exceptions.UniqueViolationError:
            return True
        return False

    async def delete_reaction_user(
        self, emoji: str, message_id: int, user_id: int
    ) -> None:
        reaction = await self.get_reaction(emoji, message_id)
        if reaction is None:
            return
        await self.execute(
            """DELETE FROM reaction_users
            WHERE reaction_id=$1 AND user_id=$2""",
            reaction["id"],
            user_id,
        )
