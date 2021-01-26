from typing import Optional

import asyncpg


class Members:
    def __init__(self, bot) -> None:
        self.bot = bot

    async def get_member(self, user_id: int, guild_id: int) -> Optional[dict]:
        return await self.bot.db.fetchrow(
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

        await self.bot.db.guilds.create_guild(guild_id)

        try:
            await self.bot.db.execute(
                """INSERT INTO members (user_id, guild_id)
                VALUES ($1, $2)""",
                user_id,
                guild_id,
            )
        except asyncpg.exceptions.UniqueViolationError:
            return True
        return False
