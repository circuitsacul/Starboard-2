from typing import Optional

import asyncpg


class Guilds:
    def __init__(self, bot) -> None:
        self.bot = bot

    async def get_guild(self, guild_id: int) -> Optional[dict]:
        sql_guild = await self.bot.db.fetchrow(
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
            await self.bot.db.execute(
                """INSERT INTO guilds (id)
                VALUES ($1)""",
                guild_id,
            )
        except asyncpg.exceptions.UniqueViolationError:
            return False
        return True
