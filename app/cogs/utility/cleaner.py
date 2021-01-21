from typing import List, Tuple

import discord

from app.classes.bot import Bot


async def clean_guild(guild: discord.Guild, bot: Bot) -> List[Tuple[str, int]]:
    starboards = await clean_starboards(guild, bot)
    star_emojis = await clean_star_emojis(guild, bot)

    return [("Starboards", starboards), ("Star Emojis", star_emojis)]


async def clean_starboards(guild: discord.Guild, bot: Bot) -> int:
    removed = 0

    sql_starboards = await bot.db.get_starboards(guild.id)
    for ss in sql_starboards:
        obj = guild.get_channel(int(ss["id"]))
        if not obj:
            await bot.db.execute(
                """DELETE FROM starboards
                WHERE id=$1""",
                ss["id"],
            )
            removed += 1

    return removed


async def clean_star_emojis(guild: discord.Guild, bot: Bot) -> int:
    removed = 0

    sql_starboards = await bot.db.get_starboards(guild.id)
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

        await bot.db.edit_starboard(
            ss["id"],
            star_emojis=new_emojis,
        )
    return removed
