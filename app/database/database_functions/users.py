from typing import Optional

import asyncpg


class Users:
    def __init__(self, db) -> None:
        self.db = db

    async def get(self, user_id: int) -> Optional[dict]:
        return await self.db.fetchrow(
            """SELECT * FROM users
            WHERE id=$1""",
            user_id,
        )

    async def create(
        self, user_id: int, is_bot: bool, check_first: bool = True
    ) -> bool:
        if check_first:
            exists = await self.get(user_id) is not None
            if exists:
                return True

        try:
            await self.db.execute(
                """INSERT INTO users (id, is_bot)
                VALUES ($1, $2)""",
                user_id,
                is_bot,
            )
        except asyncpg.exceptions.UniqueViolationError:
            return True
        return False
