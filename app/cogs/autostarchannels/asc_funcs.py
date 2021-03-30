import re
from typing import Optional

import discord

from app import utils
from app.classes.bot import Bot


def try_regex(
    bot: Bot, message: discord.Message, pattern: str
) -> Optional[re.Match]:
    try:
        result = utils.safe_regex(message.system_content, pattern)
    except TimeoutError:
        bot.dispatch(
            "guild_log",
            (
                f"I tried to match `{pattern}` to [a message]"
                f"({message.jump_url}), but it took too long. "
                "Try improving the efficiency of your regex, and "
                "feel free to join the support server for help."
            ),
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
        return False, (
            f"Messages must be at least {aschannel['min_chars']} " "characters"
        )
    if aschannel["regex"]:
        if not try_regex(bot, message, aschannel["regex"]):
            return False, f"Messages must match `{aschannel['regex']}`"
    if aschannel["exclude_regex"]:
        if not try_regex(bot, message, aschannel["exclude_regex"]):
            return False, (
                f"Messages must not match `{aschannel['exclude_regex']}`"
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
                j = message.jump_url
                bot.dispatch(
                    "guild_log",
                    (
                        f"I tried to delete [a message]({j}) that didn't "
                        f"meet the requirements of {message.channel.mention}, "
                        "but I don't have the proper permissions."
                    ),
                    "error",
                    message.guild,
                )
            else:
                try:
                    await message.author.send(
                        f"Your message in {message.channel.mention} was "
                        f"deleted, because {reason.lower()}. Here is your "
                        "message:"
                    )
                    await message.author.send(message.content)
                except discord.Forbidden:
                    pass
        return

    emojis = utils.convert_emojis(aschannel["emojis"], message.guild)
    for e in emojis:
        await message.add_reaction(e)
