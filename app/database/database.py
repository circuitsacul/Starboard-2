from typing import Optional, List

import asyncpg

from .pg_tables import ALL_TABLES
from .. import errors


class Database:
    def __init__(
        self,
        database: str,
        user: str,
        password: str
    ) -> None:
        self.name = database
        self.user = user
        self.password = password

        self.pool: asyncpg.pool.Pool = None

    async def init_database(
        self
    ) -> None:
        self.pool = await asyncpg.create_pool(
            database=self.name,
            user=self.user,
            password=self.password
        )

        async with self.pool.acquire() as con:
            async with con.transaction():
                for table in ALL_TABLES:
                    await con.execute(table)

    async def execute(
        self,
        sql: str,
        *args: list
    ) -> None:
        async with self.pool.acquire() as con:
            async with con.transaction():
                await con.execute(sql, *args)

    async def fetch(
        self,
        sql: str,
        *args: list
    ) -> List[dict]:
        async with self.pool.acquire() as con:
            async with con.transaction():
                result = await con.fetch(sql, *args)
        return result

    async def fetchrow(
        self,
        sql: str,
        *args: list
    ) -> Optional[dict]:
        async with self.pool.acquire() as con:
            async with con.transaction():
                result = await con.fetchrow(sql, *args)
        return result

    async def get_guild(
        self,
        guild_id: int
    ) -> Optional[dict]:
        sql_guild = await self.fetchrow(
            """SELECT * FROM guilds
            WHERE id=$1""", guild_id
        )
        return sql_guild

    async def create_guild(
        self,
        guild_id: int,
        check_first: bool = True
    ) -> bool:
        if check_first:
            exists = await self.get_guild(guild_id) is not None
            if exists:
                return False

        try:
            await self.execute(
                """INSERT INTO guilds (id)
                VALUES ($1)""", guild_id
            )
        except asyncpg.exceptions.ForeignKeyViolationError:
            return False
        return True

    async def get_user(
        self,
        user_id: int
    ) -> Optional[dict]:
        return await self.fetchrow(
            """SELECT * FROM users
            WHERE id=$1""", user_id
        )

    async def create_user(
        self,
        user_id: int,
        check_first: bool = True
    ) -> None:
        if check_first:
            exists = await self.get_user(user_id) is not None
            if exists:
                return True

        try:
            await self.execute(
                """INSERT INTO users (id)
                VALUES ($1)""", user_id
            )
        except asyncpg.exceptions.ForeignKeyViolationError:
            return True
        return False

    async def get_member(
        self,
        user_id: int,
        guild_id: int
    ) -> Optional[dict]:
        return await self.fetchrow(
            """SELECT * FROM members
            WHERE user_id=$1 AND guild_id=$2""",
            user_id, guild_id
        )

    async def create_member(
        self,
        user_id: int,
        guild_id: int,
        check_first: bool = True
    ) -> None:
        if check_first:
            exists = await self.get_member(user_id, guild_id)\
                is not None
            if exists:
                return True

        await self.create_guild(guild_id)
        await self.create_user(user_id)
        try:
            await self.execute(
                """INSERT INTO members (user_id, guild_id)
                VALUES ($1, $2)""", user_id, guild_id
            )
        except asyncpg.exceptions.ForeignKeyViolationError:
            return True
        return False

    async def get_starboard(
        self,
        starboard_id: int
    ) -> Optional[dict]:
        return await self.fetchrow(
            """SELECT * FROM starboards
            WHERE id=$1""", starboard_id
        )

    async def get_starboards(
        self,
        guild_id: int
    ) -> List[dict]:
        return await self.fetch(
            """SELECT * FROM starboards
            WHERE guild_id=$1""", guild_id
        )

    async def create_starboard(
        self,
        channel_id: int,
        guild_id: int,
        check_first: bool = True
    ) -> None:
        if check_first:
            exists = await self.get_starboard(
                channel_id
            ) is not None
            if exists:
                return True

        await self.create_guild(guild_id)
        try:
            await self.execute(
                """INSERT INTO starboards (id, guild_id)
                VALUES ($1, $2)""", channel_id, guild_id
            )
        except asyncpg.exceptions.ForeignKeyViolationError:
            return True
        return False

    async def edit_starboard(
        self,
        starboard_id: int = None,
        required: int = None,
        required_remove: int = None,
        self_star: bool = None,
        unstar: bool = None,
        allow_bots: bool = None,
        link_deletes: bool = None,
        images_only: bool = None,
        remove_reactions: bool = None,
        no_xp: bool = None,
        explore: bool = None,
        star_emojis: List[str] = None,
        react_emojis: List[str] = None,
        display_emoji: str = None
    ) -> None:
        s = await self.get_starboard(starboard_id)
        if not s:
            raise errors.DoesNotExist(
                f"Starboard {starboard_id} does not exist."
            )

        async with self.pool.acquire() as con:
            async with con.transaction():
                await con.execute(
                    """UPDATE starboards
                    SET required = $1,
                    required_remove = $2,
                    self_star = $3,
                    unstar = $4,
                    allow_bots = $5,
                    link_deletes = $6,
                    images_only = $7,
                    remove_reactions = $8,
                    no_xp = $9,
                    explore = $10,
                    star_emojis = $11,
                    react_emojis = $12,
                    display_emoji = $13
                    WHERE id = $14""",
                    s['required'] if required is None else required,
                    s['required_remove'] if required_remove is None else
                    required_remove,
                    s['self_star'] if self_star is None else self_star,
                    s['unstar'] if unstar is None else unstar,
                    s['allow_bots'] if allow_bots is None else allow_bots,
                    s['link_deletes'] if link_deletes is None else
                    link_deletes,
                    s['images_only'] if images_only is None else images_only,
                    s['remove_reactions'] if remove_reactions is None else
                    remove_reactions,
                    s['no_xp'] if no_xp is None else no_xp,
                    s['explore'] if explore is None else explore,
                    s['star_emojis'] if star_emojis is None else star_emojis,
                    s['react_emojis'] if react_emojis is None else
                    react_emojis,
                    s['display_emoji'] if display_emoji is None else
                    display_emoji,
                    starboard_id
                )

    async def get_setting_overrides(
        self,
        starboard: int = [],
        channel: int = [],
        roles: List[int] = []
    ) -> Optional[dict]:
        setting_overrides = await self.fetch(
            """SELECT * FROM setting_overrides
            WHERE $1::numeric = any(starboards)
            AND in_channels = '{}' or $2::numeric = any(in_channels)
            AND not_in_channels = '{}' or $2::numeric != all (not_in_channels)
            AND (EXISTS(
                    (SELECT $3::numeric[])
                    INTERSECT
                    SELECT has_roles
                ))
            AND (NOT EXISTS(
                    (SELECT $3::numeric[])
                    INTERSECT
                    SELECT lacks_roles
                ))
            ORDER BY index DESC;
            """, starboard, channel, roles
        )
        return setting_overrides
