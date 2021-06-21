from typing import TYPE_CHECKING

import config
from app.errors import NotEnoughCredits

if TYPE_CHECKING:
    from app.database.database import Database


def premium_limit_for(key: str) -> int:
    return config.PREMIUM_LIMITS.get(key, normal_limit_for(key))


def normal_limit_for(key: str) -> int:
    return config.DEFAULT_LIMITS.get(key, 0)


async def can_increase(key: str, guild_id: int, db: "Database") -> bool:
    max_limit = premium_limit_for(key)
    act_limit = await limit_for(key, guild_id, db)
    return act_limit < max_limit


async def limit_for(key: str, guild_id: int, db: "Database") -> int:
    guild = await db.guilds.get(guild_id)
    if guild["premium_end"] is not None:
        return premium_limit_for(key)
    else:
        return normal_limit_for(key)


async def redeem_credits(
    db: "Database", guild_id: int, user_id: int, months: int
):
    assert await db.guilds.get(guild_id) is not None, "guild was none"
    user = await db.users.get(user_id)

    credits = config.CREDITS_PER_MONTH * months
    if credits > user["credits"]:
        raise NotEnoughCredits()

    await db.guilds.add_months(guild_id, months)
    await db.execute(
        """UPDATE users
        SET credits=credits-$1
        WHERE id=$2""",
        credits,
        user_id,
    )
