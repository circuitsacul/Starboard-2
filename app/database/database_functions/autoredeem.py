from typing import TYPE_CHECKING, Any, Dict, List, Optional

from app import errors

if TYPE_CHECKING:
    from app.database.database import Database


class Autoredeem:
    def __init__(self, db: "Database"):
        self.db = db

    async def get(
        self, guild_id: int, user_id: int
    ) -> Optional[Dict[str, Any]]:
        return await self.db.fetchrow(
            """SELECT * FROM autoredeem
            WHERE guild_id=$1 AND user_id=$2""",
            guild_id,
            user_id,
        )

    async def find_valid(self, guild_id: int) -> List[Dict[str, Any]]:
        return await self.db.fetch(
            """SELECT * FROM autoredeem
            WHERE guild_id=$1
            AND EXISTS (
                SELECT * FROM users
                WHERE id=user_id
                AND credits >= 3
            )
            ORDER BY enabled_on DESC""",
            guild_id,
        )

    async def get_user_guilds(
        self,
        user_id: int,
    ) -> List[Dict[str, Any]]:
        return await self.db.fetch(
            """SELECT * FROM autoredeem WHERE user_id=$1""",
            user_id,
        )

    async def create(self, guild_id: int, user_id: int):
        if await self.get(guild_id, user_id):
            raise errors.AutoRedeemAlreadyOn()
        await self.db.execute(
            """INSERT INTO autoredeem (guild_id, user_id)
            VALUES ($1, $2)""",
            guild_id,
            user_id,
        )

    async def delete(self, guild_id: int, user_id: int):
        await self.db.execute(
            """DELETE FROM autoredeem
            WHERE guild_id=$1
            AND user_id=$2""",
            guild_id,
            user_id,
        )
