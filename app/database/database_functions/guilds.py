from typing import Optional

import asyncpg

from app import errors, i18n


class Guilds:
    def __init__(self, db) -> None:
        self.db = db

    async def set_locale(self, guild_id: int, locale: str) -> None:
        if locale not in i18n.locales:
            raise errors.InvalidLocale(locale)
        await self.db.execute(
            """UPDATE guilds
            SET locale=$1
            WHERE id=$2""",
            locale,
            guild_id,
        )

    async def get(self, guild_id: int) -> Optional[dict]:
        sql_guild = await self.db.fetchrow(
            """SELECT * FROM guilds
            WHERE id=$1""",
            guild_id,
        )
        return sql_guild

    async def create(self, guild_id: int, check_first: bool = True) -> bool:
        if check_first:
            exists = await self.get(guild_id) is not None
            if exists:
                return False

        try:
            await self.db.execute(
                """INSERT INTO guilds (id)
                VALUES ($1)""",
                guild_id,
            )
        except asyncpg.exceptions.UniqueViolationError:
            return False
        return True
