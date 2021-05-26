from typing import TYPE_CHECKING, Any, Dict, List, Optional

import asyncpg

from app import commands
from app.i18n import t_

if TYPE_CHECKING:
    from app.database.database import Database


class PosRoles:
    def __init__(self, db: "Database"):
        self.db = db

    async def give_posrole(self, user_id: int, role_id: int, guild_id: int):
        try:
            await self.db.execute(
                """INSERT INTO members_posroles (role_id, user_id, guild_id)
                VALUES ($1, $2, $3)""",
                role_id,
                user_id,
                guild_id,
            )
        except asyncpg.exceptions.UniqueViolationError:
            pass

    async def remove_posrole(self, user_id: int, role_id: int):
        await self.db.execute(
            """DELETE FROM members_posroles
            WHERE role_id=$1 AND user_id=$2""",
            role_id,
            user_id,
        )

    async def get_posrole_members(self, role_id: int) -> List[int]:
        return [
            d["user_id"]
            for d in await self.db.fetch(
                """SELECT user_id FROM members_posroles
                WHERE role_id=$1""",
                role_id,
            )
        ]

    async def get_member_posroles(
        self, user_id: int, guild_id: int
    ) -> List[int]:
        return [
            d["role_id"]
            for d in await self.db.fetch(
                """SELECT role_id FROM members_posroles
                WHERE user_id=$1 AND guild_id=$2""",
                user_id,
                guild_id,
            )
        ]

    async def get(self, role_id: int) -> Optional[Dict[str, Any]]:
        return await self.db.fetchrow(
            """SELECT * FROM posroles WHERE role_id=$1""", role_id
        )

    async def get_many(self, guild_id: int) -> List[Dict[str, Any]]:
        return await self.db.fetch(
            """SELECT * FROM posroles WHERE guild_id=$1""",
            guild_id,
        )

    async def create(
        self,
        role_id: int,
        guild_id: int,
        max_users: int,
    ) -> None:
        if max_users <= 0:
            raise commands.BadArgument(t_("MaxUsers must be greater than 0."))

        await self.db.execute(
            """INSERT INTO posroles
            (role_id, guild_id, max_users)
            VALUES($1, $2, $3)""",
            role_id,
            guild_id,
            max_users,
        )

    async def delete(
        self,
        role_id: int,
    ) -> None:
        await self.db.execute(
            """DELETE FROM posroles WHERE role_id=$1""",
            role_id,
        )

    async def set_max_users(
        self,
        role_id: int,
        max_users: int,
    ) -> None:
        if max_users <= 0:
            raise commands.BadArgument(t_("MaxUsers must be greater than 0."))

        await self.db.execute(
            """UPDATE posroles
            SET max_users=$1
            WHERE role_id=$2""",
            max_users,
            role_id,
        )
