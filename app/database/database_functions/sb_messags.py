from typing import TYPE_CHECKING, Optional

import asyncpg

from app import errors

if TYPE_CHECKING:
    from app.database.database import Database


class SBMessages:
    def __init__(self, db: "Database") -> None:
        self.db = db

    async def get(self, message_id: int) -> Optional[dict]:
        return await self.db.fetchrow(
            """SELECT * FROM starboard_messages
            WHERE id=$1""",
            message_id,
        )

    async def create(
        self,
        message_id: int,
        orig_id: int,
        starboard_id: int,
        check_first: bool = True,
    ) -> bool:
        if check_first:
            exists = await self.get(message_id)
            if exists:
                return True

        already_orig_message = (
            await self.db.messages.get(message_id) is not None
        )
        if already_orig_message:
            raise errors.AlreadyOrigMessage(
                f"Could not create starboard message {message_id} "
                "because it is already a normal message."
            )

        try:
            await self.db.execute(
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

    async def delete(self, message_id: int) -> None:
        await self.db.execute(
            """DELETE FROM starboard_messages WHERE id=$1""", message_id
        )
