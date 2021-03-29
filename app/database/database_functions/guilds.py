from typing import Optional

import asyncpg


class Guilds:
    def __init__(self, db) -> None:
        self.db = db

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
