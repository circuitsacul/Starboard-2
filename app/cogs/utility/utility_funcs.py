from typing import List

from app.classes.bot import Bot
from app.cogs.starboard import starboard_funcs


async def handle_freezing(
    bot: Bot,
    message_id: int,
    guild_id: int,
    freeze: bool
) -> None:
    await bot.db.execute(
        """UPDATE messages
        SET frozen=$1
        WHERE id=$2""",
        freeze, message_id
    )
    await starboard_funcs.update_message(bot, message_id, guild_id)


async def handle_forcing(
    bot: Bot,
    message_id: int,
    guild_id: int,
    _starboards: List[int],
    force: bool
) -> None:
    sql_message = await bot.db.get_message(message_id)
    if not sql_message:
        return
    new_forced: List = sql_message['forced']
    if len(_starboards) != 0:
        starboards = _starboards
    else:
        starboards = [
            s['id'] for s in await bot.db.get_starboards(guild_id)
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
        WHERE id=$2""", new_forced, message_id
    )

    await starboard_funcs.update_message(bot, message_id, guild_id)


async def handle_trashing(
    bot: Bot,
    message_id: int,
    guild_id: int,
    trash: bool
) -> None:
    await bot.db.execute(
        """UPDATE messages
        SET trashed=$1
        WHERE id=$2""",
        trash, message_id
    )
    await starboard_funcs.update_message(bot, message_id, guild_id)
