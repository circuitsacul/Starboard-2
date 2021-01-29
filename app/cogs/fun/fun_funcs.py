import discord

from app.classes.bot import Bot


async def get_guild_leaderboard(bot: Bot, guild: discord.Guild) -> dict:
    leaderboard = {}
    top_users = await bot.db.fetch(
        """SELECT * FROM members
        WHERE guild_id=$1
        ORDER BY xp DESC
        LIMIT 200""",
        guild.id,
    )
    uids = [int(u["user_id"]) for u in top_users]
    user_lookup = await bot.cache.get_members(uids, guild)
    for x, u in enumerate(top_users):
        obj = user_lookup.get(int(u["user_id"]))
        if not obj:
            continue

        leaderboard[obj.id] = {
            "name": str(obj),
            "xp": u["xp"],
            "level": u["level"],
            "rank": x + 1,
        }
    return leaderboard


async def get_rank(bot: Bot, guild: discord.Guild, user_id: int) -> int:
    lb = await get_guild_leaderboard(bot, guild)
    u = lb.get(user_id)
    return None if not u else u["xp"]
