import asyncio
import errno
import os
import re
import signal
from functools import wraps
from typing import List, Optional, Union

import discord
from discord.ext import commands


# Decoraters
def timeout(seconds=10, error_message=os.strerror(errno.ETIME)):
    def decorator(func):
        def _handle_timeout(signum, frame):
            raise TimeoutError(error_message)

        def wrapper(*args, **kwargs):
            signal.signal(signal.SIGALRM, _handle_timeout)
            signal.setitimer(signal.ITIMER_REAL, seconds)
            try:
                result = func(*args, **kwargs)
            finally:
                signal.alarm(0)
            return result

        return wraps(func)(wrapper)

    return decorator


# Functions
def jump_link(message_id: int, channel_id: int, guild_id: int) -> str:
    return (
        f"https://discord.com/channels/{guild_id}/{channel_id}"
        f"/{message_id}"
    )


def escmd(text: str) -> str:
    if type(text) is not str:
        return
    return discord.utils.escape_markdown(text)


def ms(seconds: int) -> int:
    return round(seconds * 1000, 2)


def safe_regex(string: str, pattern: str, max_time: float = 0.01) -> bool:
    @timeout(seconds=max_time)
    def run_regex(string: str, pattern: str) -> Optional[re.Match]:
        return re.match(pattern, string)

    return run_regex(string, pattern)


def clean_emoji(
    emoji: Union[str, int, discord.Emoji, discord.Reaction]
) -> str:
    animated_pattern = "^<:.*:[0-9]+>$"
    custom_pattern = "^<a:.*:[0-9]+>$"

    if type(emoji) is discord.partial_emoji.PartialEmoji:
        if emoji.id is None:
            return emoji.name
        else:
            return str(emoji.id)

    if type(emoji) is discord.Emoji:
        str_emoji = str(emoji.id)
    else:
        str_emoji = str(emoji)

    if re.match(animated_pattern, str_emoji) or re.match(
        custom_pattern, str_emoji
    ):
        return str_emoji.split(":")[-1][:-1]
    return str_emoji


def convert_emojis(
    emojis: List[Union[str, int]], guild: discord.Guild
) -> List[str]:
    result: List[str] = []
    for e in emojis:
        eid = None
        try:
            eid = int(e)
        except ValueError:
            pass

        if eid is not None:
            e_obj = discord.utils.get(guild.emojis, id=eid)
            result.append(str(e_obj))
        else:
            result.append(str(e))
    return result


def pretty_emoji_string(
    emojis: List[Union[str, int]], guild: discord.Guild
) -> str:
    if len(emojis) == 0:
        return "None"
    converted = convert_emojis(emojis, guild)
    return " ".join(converted)


async def confirm(ctx: commands.Context) -> Optional[bool]:
    def check(m) -> bool:
        if m.author.id != ctx.message.author.id:
            return False
        if m.channel.id != ctx.channel.id:
            return False
        if not m.content.lower()[0] in ["y", "n"]:
            return False
        return True

    try:
        message = await ctx.bot.wait_for("message", check=check)
    except asyncio.exceptions.TimeoutError:
        await ctx.send("Timed out.")
        return None
    if message.content.lower().startswith("y"):
        return True
    elif message.content.lower().startswith("n"):
        return False
    return await confirm(ctx)


async def paginator(ctx: commands.Context, pages: List[discord.Embed]) -> None:
    left_emoji = "⬅️"
    right_emoji = "➡️"
    stop_emoji = "⏹️"

    current_page = 0
    total_pages = len(pages)
    running = True
    message = None
    while running:
        page = pages[current_page]
        page.set_footer(text=f"{current_page+1}/{total_pages}")
        if not message:
            message = await ctx.send(embed=page)
            for e in [left_emoji, right_emoji, stop_emoji]:
                await message.add_reaction(e)
        else:
            await message.edit(embed=page)

        def check(payload: discord.RawReactionActionEvent) -> bool:
            if payload.user_id != ctx.message.author.id:
                return False
            if payload.message_id != message.id:
                return False
            if payload.emoji.name not in [left_emoji, right_emoji, stop_emoji]:
                return False
            return True

        payload = await ctx.bot.wait_for("raw_reaction_add", check=check)
        try:
            await message.remove_reaction(
                payload.emoji.name, ctx.message.author
            )
        except discord.Forbidden:
            pass
        if payload.emoji.name == left_emoji:
            current_page -= 1
        elif payload.emoji.name == right_emoji:
            current_page += 1
        elif payload.emoji.name == stop_emoji:
            running = False

        if current_page > total_pages - 1:
            current_page = 0
        elif current_page < 0:
            current_page = total_pages - 1

    if message:
        await message.delete()
