from typing import Optional

from app.classes.bot import Bot


async def orig_message(
    bot: Bot,
    message_id: int
) -> Optional[dict]:
    starboard_message = await bot.db.get_starboard_message(
        message_id
    )

    if starboard_message is not None:
        return await bot.db.get_message(
            starboard_message['orig_id']
        )

    return await bot.db.get_message(
        message_id
    )
