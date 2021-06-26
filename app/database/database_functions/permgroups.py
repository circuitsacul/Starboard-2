import typing
from typing import List, Optional

from app import errors
from app.cogs.premium.premium_funcs import can_increase, limit_for

if typing.TYPE_CHECKING:
    from app.database.database import Database


class PermGroups:
    def __init__(self, db: "Database"):
        self.db = db

    async def create(self, guild_id: int, name: str) -> int:
        name = name.casefold()
        groups = await self.get_many(guild_id)
        if name in [g["name"] for g in groups]:
            raise errors.GroupNameAlreadyExists(name)

        limit = await limit_for("permgroups", guild_id, self.db)
        if len(groups) >= limit:
            raise errors.PermGroupLimitReached(
                await can_increase("permgroups", guild_id, self.db)
            )

        if groups:
            index = max([g["index"] for g in groups]) + 1
        else:
            index = 1

        return await self.db.fetchval(
            """INSERT INTO permgroups (guild_id, name, index)
            VALUES ($1, $2, $3)""",
            guild_id,
            name,
            index,
        )

    async def delete(self, permgroup_id: int):
        group = await self.get_id(permgroup_id)
        await self.db.execute(
            """DELETE FROM permgroups
            WHERE id=$1""",
            permgroup_id,
        )
        await self.db.execute(
            """UPDATE permgroups
            SET index = index - 1
            WHERE index > $1
            AND guild_id=$2""",
            group["index"],
            group["guild_id"],
        )

    async def move(self, permgroup_id: int, new_index: int) -> int:
        group = await self.get_id(permgroup_id)
        groups = await self.get_many(group["guild_id"])

        largest_index = max([g["index"] for g in groups])
        if new_index > largest_index:
            new_index = largest_index
        elif new_index < 0:
            new_index = 1

        if new_index < group["index"]:
            direction = 1
        elif new_index > group["index"]:
            direction = -1
        else:
            return group["index"]

        await self.db.execute(
            """UPDATE permgroups
            SET index=index+$1
            WHERE guild_id=$2
            AND index BETWEEN $3 AND $4""",
            direction,
            group["guild_id"],
            min(group["index"], new_index),
            max(new_index, group["index"]),
        )
        await self.db.execute(
            """UPDATE permgroups
            SET index=$1
            WHERE id=$2""",
            new_index,
            permgroup_id,
        )
        return new_index

    async def set_starboards(self, permgroup_id: int, starboards: List[int]):
        await self.db.execute(
            """UPDATE permgroups
            SET starboards=$1
            WHERE id=$2""",
            starboards,
            permgroup_id,
        )

    async def set_channels(self, permgroup_id: int, channels: List[int]):
        await self.db.execute(
            """UPDATE permgroups
            SET channels=$1
            WHERE id=$2""",
            channels,
            permgroup_id,
        )

    async def get_many(self, guild_id: int) -> List[dict]:
        return await self.db.fetch(
            """SELECT * FROM permgroups
            WHERE guild_id=$1 ORDER BY index""",
            guild_id,
        )

    async def get_name(self, guild_id: int, name: str) -> Optional[dict]:
        return await self.db.fetchrow(
            """SELECT * FROM permgroups
            WHERE name=$1 AND guild_id=$2""",
            name.casefold(),
            guild_id,
        )

    async def get_id(self, permgroup_id: int) -> Optional[dict]:
        return await self.db.fetchrow(
            """SELECT * FROM permgroups
            WHERE id=$1""",
            permgroup_id,
        )
