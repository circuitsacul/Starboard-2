from typing import List, Optional

import asyncpg

from app import errors


class SBMessages:
    def __init__(self, bot) -> None:
        self.bot = bot

    async def get_starboard_message(self, message_id: int) -> Optional[dict]:
        return await self.bot.db.fetchrow(
            """SELECT * FROM starboard_messages
            WHERE id=$1""",
            message_id,
        )

    async def get_starboard_messages(self, orig_id: int) -> List[dict]:
        return await self.bot.db.fetch(
            """SELECT * FROM starboard_messages
            WHERE orig_id=$1"""
        )

    async def get_starboard_message_from_starboard(
        self, orig_id: int, starboard_id: int
    ) -> Optional[dict]:
        return await self.bot.db.fetchrow(
            """SELECT * FROM starboard_messages
            WHERE orig_id=$1 AND starboard_id=$2""",
            orig_id,
            starboard_id,
        )

    async def create_starboard_message(
        self,
        message_id: int,
        orig_id: int,
        starboard_id: int,
        check_first: bool = True,
    ) -> bool:
        if check_first:
            exists = await self.get_starboard_message(message_id)
            if exists:
                return True

        already_orig_message = (
            await self.bot.db.messages.get_message(message_id) is not None
        )
        if already_orig_message:
            raise errors.AlreadyOrigMessage(
                f"Could not create starboard message {message_id} "
                "because it is already a normal message."
            )

        try:
            await self.bot.db.execute(
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
