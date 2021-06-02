from typing import TYPE_CHECKING, Any, Dict, List

from app import commands, errors
from app.i18n import t_

if TYPE_CHECKING:
    from app.database.database import Database


class XPRoles:
    def __init__(self, db: "Database"):
        self.db = db

    async def get(self, role_id: int) -> dict:
        return await self.db.fetchrow(
            """SELECT * FROM xproles WHERE role_id=$1""", role_id
        )

    async def get_many(self, guild_id: int) -> List[Dict[Any, Any]]:
        return await self.db.fetch(
            """SELECT * FROM xproles WHERE guild_id=$1""", guild_id
        )

    async def create(
        self,
        role_id: int,
        guild_id: int,
        required: int,
    ):
        if required <= 0:
            raise commands.BadArgument(t_("Required must be greater than 0."))

        if await self.db.posroles.get(role_id) is not None:
            raise errors.PosRoleAndXpRole()

        await self.db.execute(
            """INSERT INTO xproles (role_id, guild_id, required)
            VALUES ($1, $2, $3)""",
            role_id,
            guild_id,
            required,
        )

    async def delete(self, role_id: int):
        await self.db.execute(
            """DELETE FROM xproles WHERE role_id=$1""", role_id
        )

    async def set_required(self, role_id: int, required: int):
        if required <= 0:
            raise commands.BadArgument(t_("Required must be greater than 0."))
        await self.db.execute(
            """UPDATE xproles SET required=$1
            WHERE role_id=$2""",
            required,
            role_id,
        )
