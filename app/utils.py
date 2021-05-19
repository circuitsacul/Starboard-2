import errno
import os
import re
import signal
import typing
from functools import wraps
from typing import Any, Dict, Generator, Iterable, List, Optional, Tuple, Union

import discord
from discord import RequestsWebhookAdapter, Webhook
from discord.ext import commands

from app.classes.context import MyContext
from app.constants import ARROW_RIGHT
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
async def get_prefix(
    bot: "Bot", message: discord.Message, when_mentioned: bool = True
) -> List[str]:
    if message.guild:
        guild = await bot.db.guilds.get(message.guild.id)
        if not guild:
            prefixes = ["sb!"]
        else:
            prefixes = guild["prefixes"]
    else:
        prefixes = ["sb!"]
    prefixes = list(sorted(prefixes, key=len, reverse=True))
    if when_mentioned:
        return commands.when_mentioned_or(*prefixes)(bot, message)
    return prefixes


def webhooklog(content: str, url: Optional[str]) -> None:
    if not url:
        return
    webhook = Webhook.from_url(url, adapter=RequestsWebhookAdapter())
    webhook.send(content, username="Starboard Uptime")


def get_intersect(list1: Iterable[Any], list2: Iterable[Any]) -> List[Any]:
    return [value for value in list1 if value in list2]


def chunk_list(
    lst: List[Any], max_size: int
) -> Generator[List[Any], None, None]:
    """Use list(chunk_list(...)) or for lst in chunk_list(...)"""
    for i in range(0, len(lst), max_size):
        yield lst[i : i + max_size]


def cs_embed(
    changes: Dict[str, Tuple[Any, Any]], bot: "Bot", noticks: bool = False
) -> discord.Embed:
    text = cs_text(changes, noticks=noticks)
    return discord.Embed(
        title=t_("Changed Settings:"), description=text, color=bot.theme_color
    )


def cs_text(changes: Dict[str, Tuple[Any, Any]], noticks: bool = False) -> str:
    t = "" if noticks else "`"
    text = "\n".join(
        [
            f"{name}: "
            f"{t}{o[0] if o[0] not in [None, ''] else 'None'}{t}"
            f" **{ARROW_RIGHT}** "
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
    return discord.utils.escape_markdown(text)


def escmask(text: str) -> str:
    """Escapes link markdown by adding \\ before \"[\" and \"]\""""
    text = escesc(text)
    text = text.replace("]", "\\]")
    text = text.replace("[", "\\[")
    return text


def ms(seconds: float) -> float:
    return round(seconds * 1000, 2)


def safe_regex(
    string: str, pattern: str, max_time: float = 0.01
) -> Optional[re.Match]:
    @timeout(seconds=max_time)
    def run_regex(string: str, pattern: str) -> Optional[re.Match]:
        return re.search(pattern, string)

    return run_regex(string, pattern)


def clean_emoji(
    emoji: Union[str, int, discord.Emoji, discord.Reaction]
) -> str:
    animated_pattern = "^<:.*:[0-9]+>$"
    custom_pattern = "^<a:.*:[0-9]+>$"

    if isinstance(emoji, discord.partial_emoji.PartialEmoji):
        if emoji.id is None:
            return emoji.name
        else:
            return str(emoji.id)

    if isinstance(emoji, discord.Emoji):
        str_emoji = str(emoji.id)
    else:
        str_emoji = str(emoji)

    if re.match(animated_pattern, str_emoji) or re.match(
        custom_pattern, str_emoji
    ):
        return str_emoji.split(":")[-1][:-1]
    return str_emoji


def convert_emojis(
    emojis: List[Union[str, int, discord.Emoji]], guild: discord.Guild
) -> List[str]:
    result: List[str] = []
    for e in emojis:
        eid = None
        if not isinstance(e, discord.Emoji):
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
    emojis: List[Union[str, int, discord.Emoji]], guild: discord.Guild
) -> str:
    if len(emojis) == 0:
        return t_("None")
    converted = convert_emojis(emojis, guild)
    return " ".join(converted)


def pretty_channel_string(channels: List[int], guild: discord.Guild) -> str:
    return ", ".join([f"<#{c}>" for c in channels]) or t_("None")


def clean_prefix(ctx: "MyContext"):
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


def clean_prefix_no_ctx(prefix: str, me: Union[discord.Member, discord.User]):
    pattern = re.compile(f"<@!?{me.id}>")
    display_name = me.display_name.replace("\\", r"\\")
    return pattern.sub(f"@{display_name}", prefix)
