import discord

from app.classes.bot import Bot
from app.i18n import t_


async def clean_guild(guild: discord.Guild, bot: Bot) -> list[tuple[str, int]]:
    starboards = await clean_starboards(guild, bot)
    star_emojis = await clean_star_emojis(guild, bot)
    aschannels = await clean_aschannels(guild, bot)
    asemojis = await clean_asemojis(guild, bot)
    channel_bl = await clean_channel_blacklist(guild, bot)
    channel_wl = await clean_channel_whitelist(guild, bot)

    return [
        (t_("Starboards"), starboards),
        (t_("Star Emojis"), star_emojis),
        (t_("AutoStarChannels"), aschannels),
        (t_("AutoStar emojis"), asemojis),
        (t_("Blacklisted Channels"), channel_bl),
        (t_("Whitelisted Channels"), channel_wl),
    ]


async def clean_starboards(guild: discord.Guild, bot: Bot) -> int:
    removed = 0

    sql_starboards = await bot.db.starboards.get_many(guild.id)
    for ss in sql_starboards:
        obj = guild.get_channel(int(ss["id"]))
        if not obj:
            await bot.db.starboards.delete(ss["id"])
            removed += 1

    return removed


async def clean_star_emojis(guild: discord.Guild, bot: Bot) -> int:
    removed = 0

    sql_starboards = await bot.db.starboards.get_many(guild.id)
    for ss in sql_starboards:
        all_emojis = ss["star_emojis"]

        new_emojis = all_emojis.copy()
        for e in all_emojis:
            try:
                eid = int(e)
            except ValueError:
                continue
            obj = discord.utils.get(guild.emojis, id=eid)
            if not obj:
                new_emojis.remove(e)
                removed += 1

        await bot.db.starboards.edit(
            ss["id"],
            star_emojis=new_emojis,
        )
    return removed


async def clean_channel_blacklist(guild: discord.Guild, bot: Bot) -> int:
    removed = 0

    starboards = await bot.db.starboards.get_many(guild.id)
    for s in starboards:
        new_bl = s["channel_bl"].copy()
        for bl in s["channel_bl"]:
            obj = guild.get_channel(int(bl))
            if not obj:
                new_bl.remove(bl)
                removed += 1
        await bot.db.starboards.edit(s["id"], channel_bl=new_bl)

    return removed


async def clean_channel_whitelist(guild: discord.Guild, bot: Bot) -> int:
    removed = 0

    starboards = await bot.db.starboards.get_many(guild.id)
    for s in starboards:
        new_wl = s["channel_wl"].copy()
        for wl in s["channel_wl"]:
            obj = guild.get_channel(int(wl))
            if not obj:
                new_wl.remove(wl)
                removed += 1
        await bot.db.starboards.edit(s["id"], channel_wl=new_wl)

    return removed


async def clean_aschannels(guild: discord.Guild, bot: Bot) -> int:
    removed = 0

    sql_aschannels = await bot.db.aschannels.get_many(guild.id)
    for sasc in sql_aschannels:
        obj = guild.get_channel(int(sasc["id"]))
        if not obj:
            await bot.db.aschannels.delete(sasc["id"])
            removed += 1

    return removed


async def clean_asemojis(guild: discord.Guild, bot: Bot) -> int:
    removed = 0

    sql_aschannels = await bot.db.aschannels.get_many(guild.id)
    for sasc in sql_aschannels:
        all_emojis = sasc["emojis"]

        new_emojis = all_emojis.copy()
        for e in all_emojis:
            try:
                eid = int(e)
            except ValueError:
                continue
            obj = discord.utils.get(guild.emojis, id=eid)
            if not obj:
                new_emojis.remove(e)
                removed += 1

        await bot.db.aschannels.edit(sasc["id"], emojis=new_emojis)

    return removed
