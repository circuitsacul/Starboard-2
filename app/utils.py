import asyncio
import re
from typing import List, Optional, Union

import discord
from discord.ext import commands

from functools import wraps
import errno
import os
import signal


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
def ms(seconds: int) -> int:
    return round(seconds*1000, 1)


def safe_regex(string: str, pattern: str, max_time: float = 0.1) -> bool:
    @timeout(seconds=max_time)
    def run_regex(string: str, pattern: str) -> Optional[re.Match]:
        re.match(pattern, string)

    return run_regex(string, pattern) is not None


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

    if re.match(animated_pattern, str_emoji) or \
            re.match(custom_pattern, str_emoji):
        return str_emoji.split(':')[-1][:-1]
    return str_emoji


def convert_emojis(
    emojis: List[Union[str, int]],
    guild: discord.Guild
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
    emojis: List[Union[str, int]],
    guild: discord.Guild
) -> str:
    if len(emojis) == 0:
        return "None"
    converted = convert_emojis(emojis, guild)
    return ' '.join(converted)


async def confirm(
    ctx: commands.Context
) -> Optional[bool]:
    def check(m) -> bool:
        if m.author.id != ctx.message.author.id:
            return False
        if m.channel.id != ctx.channel.id:
            return False
        if not m.content.lower()[0] in ['y', 'n']:
            return False
        return True

    try:
        message = await ctx.bot.wait_for('message', check=check)
    except asyncio.exceptions.TimeoutError:
        await ctx.send("Timed out.")
        return None
    if message.content.lower().startswith('y'):
        return True
    elif message.content.lower().startswith('n'):
        return False
    return await confirm(ctx)
