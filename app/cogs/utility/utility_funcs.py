from typing import List, Optional, Tuple

import discord

from app.classes.bot import Bot
from app.cogs.starboard import starboard_funcs


async def handle_purging(
    bot: Bot,
    channel: discord.TextChannel,
    limit: int,
    trash: bool,
    by: Optional[discord.Member],
    notby: Optional[discord.Member],
    contains: Optional[str],
) -> Tuple[int, dict]:
    purged = {}
    total = 0

    def check(m: discord.Message) -> bool:
        if by and m.author.id != by.id:
            return False
        if notby and m.author.id == notby.id:
            return False
        if contains and contains not in m.content:
            return False
        return True

    async for m in channel.history(limit=limit + 1):
        if not check(m):
            continue
        sql_message = await starboard_funcs.orig_message(bot, m.id)
        if not sql_message:
            continue
        await handle_trashing(
            bot,
            sql_message["id"],
            sql_message["guild_id"],
            trash,
            reason="Message Purging" if trash else None,
        )
        purged.setdefault(m.author, 0)
        purged[m.author] += 1
        total += 1

    return total, purged


async def handle_freezing(
    bot: Bot, message_id: int, guild_id: int, freeze: bool
) -> None:
    await bot.db.execute(
        """UPDATE messages
        SET frozen=$1
        WHERE id=$2""",
        freeze,
        message_id,
    )
    await starboard_funcs.update_message(bot, message_id, guild_id)


async def handle_forcing(
    bot: Bot,
    message_id: int,
    guild_id: int,
    _starboards: List[int],
    force: bool,
) -> None:
    sql_message = await bot.db.messages.get(message_id)
    if not sql_message:
        return
    new_forced: List = sql_message["forced"]
    if len(_starboards) != 0:
        starboards = _starboards
    else:
        starboards = [
            s["id"] for s in await bot.db.starboards.get_many(guild_id)
        ]
    if force:
        for s in starboards:
            if s in new_forced:
                continue
            new_forced.append(s)
    else:
        for s in starboards:
            if s not in new_forced:
                continue
            new_forced.remove(s)

    await bot.db.execute(
        """UPDATE messages
        SET forced=$1::numeric[]
        WHERE id=$2""",
        new_forced,
        message_id,
    )

    await starboard_funcs.update_message(bot, message_id, guild_id)


async def set_trash_reason(
    bot: Bot, message_id: int, guild_id: int, reason: str
) -> None:
    await bot.db.execute(
        """UPDATE messages
        SET trash_reason=$1
        WHERE id=$2""",
        reason,
        message_id,
    )
    await starboard_funcs.update_message(bot, message_id, guild_id)


async def handle_trashing(
    bot: Bot, message_id: int, guild_id: int, trash: bool, reason: str = None
) -> None:
    await bot.db.execute(
        """UPDATE messages
        SET trashed=$1,
        trash_reason=$2
        WHERE id=$3""",
        trash,
        reason,
        message_id,
    )
    await starboard_funcs.update_message(bot, message_id, guild_id)
