from typing import TYPE_CHECKING, Optional

import asyncpg

if TYPE_CHECKING:
    from app.database.database import Database


class Users:
    def __init__(self, db: "Database") -> None:
        self.db = db

    async def set_patron_status(
        self,
        user_id: int,
        status: str,
    ):
        await self.db.execute(
            """UPDATE users SET patron_status=$1 WHERE id=$2""",
            status,
            user_id,
        )

    async def add_vote(self, user_id: int):
        await self.db.execute(
            """UPDATE users
            SET votes = votes + 1
            WHERE id=$1""",
            user_id,
        )

    async def edit(
        self,
        user_id: int,
        locale: str = None,
        public: bool = None,
    ) -> None:
        user = await self.get(user_id)

        settings = {
            "locale": user["locale"] if locale is None else locale,
            "public": user["public"] if public is None else public,
        }

        await self.db.execute(
            """UPDATE users
            SET locale=$1,
            public=$2
            WHERE id=$3""",
            settings["locale"],
            settings["public"],
            user_id,
        )

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
