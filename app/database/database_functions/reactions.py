from typing import TYPE_CHECKING, Optional

import asyncpg

from app import errors

if TYPE_CHECKING:
    from app.database.database import Database


class Reactions:
    def __init__(self, db: "Database") -> None:
        self.db = db

    async def get_reaction(
        self, emoji: str, message_id: int
    ) -> Optional[dict]:
        return await self.db.fetchrow(
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
            await self.db.execute(
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
        return await self.db.fetchrow(
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
        if not reaction:
            raise errors.NotInDatabase(
                f"Created reaction {emoji}, {message_id}, but "
                "count not find it."
            )

        try:
            await self.db.execute(
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
        await self.db.execute(
            """DELETE FROM reaction_users
            WHERE reaction_id=$1 AND user_id=$2""",
            reaction["id"],
            user_id,
        )
