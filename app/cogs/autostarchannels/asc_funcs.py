import re
from typing import Optional

import discord

from app import utils
from app.classes.bot import Bot
from i18n import t_


def try_regex(
    bot: Bot, message: discord.Message, pattern: str
) -> Optional[re.Match]:
    try:
        result = utils.safe_regex(message.system_content, pattern)
    except TimeoutError:
        bot.dispatch(
            "guild_log",
            t_(
                "I tried to match `{0}` to [a message]"
                "({1.jump_url}), but it took too long. "
                "Try improving the efficiency of your regex, and "
                "feel free to join the support server for help."
            ).format(pattern, message),
        )
        return True
    if result is not None:
        return True
    return False


def is_valid(
    bot: Bot, message: discord.Message, aschannel: dict
) -> tuple[bool, str]:
    if aschannel["require_image"]:
        if len(message.attachments) == 0:
            return False, "Messages must have an image attached"
    if len(message.system_content) < aschannel["min_chars"]:
        return False, t_("Messages must be at least {0} characters").format(
            aschannel["min_chars"]
        )
    if aschannel["regex"]:
        if not try_regex(bot, message, aschannel["regex"]):
            return False, t_("Messages must match `{0}`").format(
                aschannel["regex"]
            )
    if aschannel["exclude_regex"]:
        if not try_regex(bot, message, aschannel["exclude_regex"]):
            return False, t_(f"Messages must not match `{0}`").format(
                aschannel["exclude_regex"]
            )
    return True, ""


async def handle_message(
    bot: Bot, message: discord.Message, aschannel: dict
) -> None:
    valid, reason = is_valid(bot, message, aschannel)
    if not valid:
        if aschannel["delete_invalid"]:
            try:
                await message.delete()
            except discord.Forbidden:
                bot.dispatch(
                    "guild_log",
                    t_(
                        "I tried to delete [a message]({0.jump_url}) that "
                        "didn't meet the requirements of {0.channel.mention}, "
                        "but I don't have the proper permissions."
                    ).format(message),
                    "error",
                    message.guild,
                )
            else:
                try:
                    await message.author.send(
                        t_(
                            "Your message in {0} was "
                            "deleted, because {1}. Here is your "
                            "message:"
                        ).format(message.channel.mention, reason.lower())
                    )
                    await message.author.send(message.content)
                except discord.Forbidden:
                    pass
        return

    emojis = utils.convert_emojis(aschannel["emojis"], message.guild)
    for e in emojis:
        await message.add_reaction(e)
