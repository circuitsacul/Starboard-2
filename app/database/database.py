from typing import Optional, List

import asyncpg

from .pg_tables import ALL_TABLES


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
        print("Opening Database")
        self.pool = await asyncpg.create_pool(
            database=self.name,
            user=self.user,
            password=self.password
        )

        async with self.pool.acquire() as con:
            async with con.transaction():
                for table in ALL_TABLES:
                    await con.execute(table)
        print("Database opened")

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
