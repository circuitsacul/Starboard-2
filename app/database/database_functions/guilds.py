import datetime
from typing import TYPE_CHECKING, Optional

import asyncpg
from aiocache import Cache, SimpleMemoryCache

from app import commands, constants, errors, i18n
from app.i18n import t_

if TYPE_CHECKING:
    from app.database.database import Database


class Guilds:
    def __init__(self, db: "Database") -> None:
        self.db = db
        self.cache: SimpleMemoryCache = Cache(namespace="guilds", ttl=10)

    async def delete(self, guild_id: int):
        await self.db.execute("""DELETE FROM guilds WHERE id=$1""", guild_id)
        await self.cache.delete(guild_id)

    async def add_months(self, guild_id: int, months: int):
        guild = await self.get(guild_id)
        current: datetime.datetime = (
            guild["premium_end"] or datetime.datetime.utcnow()
        )
        to_add = datetime.timedelta(days=constants.PREMIUM_MONTH_DAYS * months)
        await self.db.execute(
            """UPDATE guilds
            SET premium_end=$1
            WHERE id=$2""",
            current + to_add,
            guild_id,
        )

    async def set_xprole_stack(self, guild_id: int, stack: bool):
        await self.db.execute(
            """UPDATE guilds
            SET stack_xp_roles=$1
            WHERE id=$2""",
            stack,
            guild_id,
        )
        await self.cache.delete(guild_id)

    async def set_posrole_stack(self, guild_id: int, stack: bool):
        await self.db.execute(
            """UPDATE guilds
            SET stack_pos_roles=$1
            WHERE id=$2""",
            stack,
            guild_id,
        )
        await self.cache.delete(guild_id)

    async def set_cooldown(self, guild_id: int, ammount: int, per: int):
        if ammount < 1:
            raise commands.BadArgument(
                t_("The cooldown amount must be greater than 0.")
            )
        if per < 0:
            raise commands.BadArgument(
                t_("The cooldown time must be 0 or greater.")
            )
        if per > 600:
            raise commands.BadArgument(
                t_(
                    "The cooldown time can be at most 10 minutes "
                    "(600 seconds)."
                )
            )

        await self.db.execute(
            """UPDATE guilds
            SET xp_cooldown=$1,
            xp_cooldown_per=$2
            WHERE id=$3""",
            ammount,
            per,
            guild_id,
        )
        await self.cache.delete(guild_id)

    async def set_cooldown_enabled(self, guild_id: int, enabled: bool):
        await self.db.execute(
            """UPDATE guilds
            SET xp_cooldown_on=$1
            WHERE id=$2""",
            enabled,
            guild_id,
        )
        await self.cache.delete(guild_id)

    async def set_locale(self, guild_id: int, locale: str) -> None:
        if locale not in i18n.locales:
            raise errors.InvalidLocale(locale)
        await self.db.execute(
            """UPDATE guilds
            SET locale=$1
            WHERE id=$2""",
            locale,
            guild_id,
        )
        await self.cache.delete(guild_id)

    async def get(self, guild_id: int) -> Optional[dict]:
        r = await self.cache.get(guild_id)
        if r:
            return r
        sql_guild = await self.db.fetchrow(
            """SELECT * FROM guilds
            WHERE id=$1""",
            guild_id,
        )
        await self.cache.set(guild_id, sql_guild)
        return sql_guild

    async def create(self, guild_id: int, check_first: bool = True) -> bool:
        if check_first:
            exists = await self.get(guild_id) is not None
            if exists:
                return False

        try:
            await self.db.execute(
                """INSERT INTO guilds (id)
                VALUES ($1)""",
                guild_id,
            )
        except asyncpg.exceptions.UniqueViolationError:
            return False
        await self.cache.delete(guild_id)
        return True
