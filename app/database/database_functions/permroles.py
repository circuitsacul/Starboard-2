import typing
from typing import Any, Dict, List, Optional

import buildpg

from app import errors
from app.cogs.premium.premium_funcs import can_increase, limit_for

if typing.TYPE_CHECKING:
    from app.database.database import Database


class PermRoles:
    def __init__(self, db: "Database"):
        self.db = db

    async def create(self, permgroup_id: int, role_id: int):
        permroles = await self.get_many(permgroup_id)

        permgroup = await self.db.permgroups.get_id(permgroup_id)
        guild_id = int(permgroup["guild_id"])
        limit = await limit_for("permroles", guild_id, self.db)
        if len(permroles) >= limit:
            raise errors.PermRoleLimitReached(
                await can_increase("permroles", guild_id, self.db)
            )

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

    async def get_many(self, group_id: int) -> List[Dict[Any, Any]]:
        return await self.db.fetch(
            """SELECT * FROM permroles
            WHERE permgroup_id=$1 ORDER BY index""",
            group_id,
        )

    async def get(
        self, role_id: int, group_id: int
    ) -> Optional[Dict[Any, Any]]:
        return await self.db.fetchrow(
            """SELECT * FROM permroles
            WHERE role_id=$1
            AND permgroup_id=$2""",
            role_id,
            group_id,
        )

    async def edit(self, role_id: int, group_id: int, **attrs):
        valid_settings = [
            "allow_commands",
            "on_starboard",
            "give_stars",
            "gain_xp",
            "pos_roles",
            "xp_roles",
        ]

        permrole = await self.get(role_id, group_id)
        if not permrole:
            raise errors.PermRoleNotFound(role_id, group_id)

        settings = {}
        for key in valid_settings:
            settings[key] = attrs.get(key, permrole[key])

        query, args = buildpg.render(
            """UPDATE permroles
            SET allow_commands=:allow_commands,
            on_starboard=:on_starboard,
            give_stars=:give_stars,
            gain_xp=:gain_xp,
            pos_roles=:pos_roles,
            xp_roles=:xp_roles
            WHERE role_id=:role_id AND permgroup_id=:group_id""",
            **settings,
            role_id=role_id,
            group_id=group_id,
        )

        await self.db.execute(query, *args)
