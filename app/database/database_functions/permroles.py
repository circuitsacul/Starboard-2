import typing
from typing import Optional

if typing.TYPE_CHECKING:
    from app.database.database import Database


class PermRoles:
    def __init__(self, db: "Database"):
        self.db = db

    async def create(self, permgroup_id: int, role_id: int):
        permroles = await self.get_many(permgroup_id)
        if permroles:
            next_index = max(pr["index"] for pr in permroles) + 1
        else:
            next_index = 1

        await self.db.execute(
            """INSERT INTO permroles
            (permgroup_id, role_id, index)
            VALUES ($1, $2, $3)""",
            permgroup_id,
            role_id,
            next_index,
        )

    async def delete(self, role_id: int, group_id: int):
        permrole = await self.get(role_id, group_id)
        await self.db.execute(
            """DELETE FROM permroles WHERE role_id=$1 AND permgroup_id=$2""",
            role_id,
            group_id,
        )
        await self.db.execute(
            """UPDATE permroles
            SET index = index - 1
            WHERE permgroup_id=$1
            AND index > $2""",
            group_id,
            permrole["index"],
        )

    async def move(self, role_id: int, group_id: int, index: int) -> int:
        permroles = await self.get_many(group_id)
        permrole = await self.get(role_id, group_id)

        largest_index = max(pr["index"] for pr in permroles)

        if index > largest_index:
            index = largest_index
        elif index < 1:
            index = 1

        if index > permrole["index"]:
            direction = -1
        elif index < permrole["index"]:
            direction = 1
        else:
            return permrole["index"]

        await self.db.execute(
            """UPDATE permroles
            SET index = index + $1
            WHERE permgroup_id=$2
            AND index BETWEEN $3 AND $4""",
            direction,
            group_id,
            min(index, permrole["index"]),
            max(index, permrole["index"]),
        )
        await self.db.execute(
            """UPDATE permroles
            SET index=$1
            WHERE role_id=$2
            AND permgroup_id=$3""",
            index,
            role_id,
            group_id,
        )

        return index

    async def get_many(self, group_id: int) -> list[dict]:
        return await self.db.fetch(
            """SELECT * FROM permroles
            WHERE permgroup_id=$1 ORDER BY index""",
            group_id,
        )

    async def get(self, role_id: int, group_id: int) -> Optional[dict]:
        return await self.db.fetchrow(
            """SELECT * FROM permroles
            WHERE role_id=$1
            AND permgroup_id=$2""",
            role_id,
            group_id,
        )

    async def set_allow_commands(
        self,
        role_id: int,
        group_id: int,
        allow_commands: Optional[bool],
    ):
        await self.db.execute(
            """UPDATE permroles
            SET allow_commands=$1
            WHERE role_id=$2
            AND permgroup_id=$3""",
            allow_commands,
            role_id,
            group_id,
        )

    async def set_on_starboard(
        self,
        role_id: int,
        group_id: int,
        on_starboard: Optional[bool],
    ):
        await self.db.execute(
            """UPDATE permroles
            SET on_starboard=$1
            WHERE role_id=$2
            AND permgroup_id=$3""",
            on_starboard,
            role_id,
            group_id,
        )

    async def set_give_stars(
        self,
        role_id: int,
        group_id: int,
        give_stars: Optional[bool],
    ):
        await self.db.execute(
            """UPDATE permroles
            SET give_stars=$1
            WHERE role_id=$2
            AND permgroup_id=$3""",
            give_stars,
            role_id,
            group_id,
        )

    async def set_gain_xp(
        self,
        role_id: int,
        group_id: int,
        gain_xp: Optional[bool],
    ):
        await self.db.execute(
            """UPDATE permroles
            SET gain_xp=$1
            WHERE role_id=$2
            AND permgroup_id=$3""",
            gain_xp,
            role_id,
            group_id,
        )

    async def set_pos_roles(
        self,
        role_id: int,
        group_id: int,
        pos_roles: Optional[bool],
    ):
        await self.db.execute(
            """UPDATE permroles
            SET pos_roles=$1
            WHERE role_id=$2
            AND permgroup_id=$3""",
            pos_roles,
            role_id,
            group_id,
        )

    async def set_xp_roles(
        self,
        role_id: int,
        group_id: int,
        xp_roles: Optional[bool],
    ):
        await self.db.execute(
            """UPDATE permroles
            SET xp_roles=$1
            WHERE role_id=$2
            AND permgroup_id=$3""",
            xp_roles,
            role_id,
            group_id,
        )
