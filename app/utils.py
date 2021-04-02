import errno
import os
import re
import signal
import typing
from functools import wraps
from typing import Any, Iterable, Optional, Union

import discord
from discord.ext import commands
from discord import RequestsWebhookAdapter, Webhook

from app.i18n import t_

if typing.TYPE_CHECKING:
    from app.classes.bot import Bot


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
def webhooklog(content: str, url: str) -> None:
    if not url:
        return
    webhook = Webhook.from_url(url, adapter=RequestsWebhookAdapter())
    webhook.send(content, username="Starboard Uptime")


def get_intersect(list1: Iterable[Any], list2: Iterable[Any]) -> list[Any]:
    return [value for value in list1 if value in list2]


def chunk_list(lst: list[Any], max_size: int) -> list[Any]:
    """Use list(chunk_list(...)) or for lst in chunk_list(...)"""
    for i in range(0, len(lst), max_size):
        yield lst[i : i + max_size]


def cs_embed(
    changes: dict[str, tuple[Any, Any]], bot: "Bot", noticks: bool = False
) -> discord.Embed:
    text = cs_text(changes, noticks=noticks)
    return discord.Embed(
        title=t_("Changed Settings:"), description=text, color=bot.theme_color
    )


def cs_text(changes: dict[str, tuple[Any, Any]], noticks: bool = False) -> str:
    t = "" if noticks else "`"
    text = "\n".join(
        [
            f"{name}: "
            f"{t}{o[0] if o[0] not in [None, ''] else 'None'}{t}"
            " **-->** "
            f"{t}{o[1] if o[1] not in [None, ''] else 'None'}{t}"
            for name, o in changes.items()
        ]
    )
    if text == "":
        text = t_("No changed settings.")
    return text


def jump_link(message_id: int, channel_id: int, guild_id: int) -> str:
    return (
        f"https://discord.com/channels/{guild_id}/{channel_id}"
        f"/{message_id}"
    )


def escesc(text: str) -> str:
    """Escapes \\ by adding another \\ behind it. Run before
    running escmd, escmask, or discord.utils.escape_markdown.
    """
    text = text.replace("\\", "\\\\")
    return text


def escmd(text: str) -> str:
    if type(text) is not str:
        return
    return discord.utils.escape_markdown(text)


def escmask(text: str) -> str:
    """Escapes link markdown by adding \\ before \"[\" and \"]\""""
    text = escesc(text)
    text = text.replace("]", "\\]")
    text = text.replace("[", "\\[")
    return text


def ms(seconds: int) -> int:
    return round(seconds * 1000, 2)


def safe_regex(
    string: str, pattern: str, max_time: float = 0.01
) -> Optional[re.Match]:
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
    emojis: list[Union[str, int, discord.Emoji]], guild: discord.Guild
) -> list[str]:
    result: list[str] = []
    for e in emojis:
        eid = None
        if type(e) is not discord.Emoji:
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
    emojis: list[Union[str, int, discord.Emoji]], guild: discord.Guild
) -> str:
    if len(emojis) == 0:
        return t_("None")
    converted = convert_emojis(emojis, guild)
    return " ".join(converted)


def pretty_channel_string(channels: list[int], guild: discord.Guild) -> str:
    return ", ".join([f"<#{c}>" for c in channels]) or t_("None")


def clean_prefix(ctx: commands.Context):
    """:class:`str`: The cleaned up invoke prefix. i.e. mentions
    are ``@name`` instead of ``<@id>``."""
    user = ctx.guild.me if ctx.guild else ctx.bot.user
    # this breaks if the prefix mention is not the bot itself but I
    # consider this to be an *incredibly* strange use case. I'd rather go
    # for this common use case rather than waste performance for the
    # odd one.
    pattern = re.compile(r"<@!?%s>" % user.id)
    return pattern.sub(
        "@%s" % user.display_name.replace("\\", r"\\"), ctx.prefix
    )
