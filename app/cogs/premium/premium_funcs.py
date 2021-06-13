from typing import TYPE_CHECKING

import config

if TYPE_CHECKING:
    from app.classes.bot import Bot


def premium_limit_for(key: str) -> int:
    return config.PREMIUM_LIMITS.get(key, normal_limit_for(key))


def normal_limit_for(key: str) -> int:
    return config.DEFAULT_LIMITS.get(key, 0)


async def limit_for(key: str, guild_id: int, bot: "Bot") -> int:
    guild = await bot.db.guilds.get(guild_id)
    if guild["premium_end"] is not None:
        return premium_limit_for(key)
    else:
        return normal_limit_for(key)


async def redeem_credits(bot: "Bot", guild_id: int, user_id: int, months: int):
    assert await bot.db.guilds.get(guild_id) is not None, "guild was none"
    user = await bot.db.users.get(user_id)

    credits = config.CREDITS_PER_MONTH * months
    if credits > user["credits"]:
        # TODO: Raise actual exception
        raise Exception

    await bot.db.guilds.add_months(guild_id, months)
    await bot.db.execute(
        """UPDATE users
        SET credits=credits-$1
        WHERE id=$2""",
        credits,
        user_id,
    )
