import typing
from typing import Optional

if typing.TYPE_CHECKING:
    from app.database.database import Database


class PermRoles:
    def __init__(self, db: Database):
        self.db = db

    async def create(self, permgroup_id: int, role_id: int):
        permroles = await self.get_many(permgroup_id)
        if permroles:
            next_index = max(pr["index"] for pr in permroles) + 1
        else:
            next_index = 1

        await self.db.execute(
            """INSERT INTO permroles
            (permgroup_id, role_id, index)""",
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
            index = largest_index + 1
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
            AND permgroup_id=$2""",
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
            AND group_id=$2""",
            role_id,
            group_id,
        )
