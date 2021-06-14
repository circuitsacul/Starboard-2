import errno
import os
import re
import signal
import typing
from functools import wraps
from typing import Any, Dict, Generator, Iterable, List, Optional, Tuple, Union

import discord
from discord import RequestsWebhookAdapter, Webhook

from app import commands
from app.classes.context import MyContext
from app.constants import ARROW_RIGHT
from app.i18n import t_

if typing.TYPE_CHECKING:
    from app.classes.bot import Bot


# Decoraters
def timeout(seconds=10, error_message=os.strerror(errno.ETIME)):
    """Sets a timeout for a function.

    :param seconds: The number of seconds to wait before timeout,
        defaults to 10
    :type seconds: Union[int, str], optional
    :param error_message: The message to raise at timeout, defaults to
        os.strerror(errno.ETIME)
    :type error_message: str, optional
    """

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
    """Get the prefixes for the current context.

    :param bot: The bot instance
    :type bot: Bot
    :param message: The message object
    :type message: discord.Message
    :param when_mentioned: Include mentions in the list of prefixes,
        defaults to True
    :type when_mentioned: bool, optional
    :return: The list of prefixes
    :rtype: List[str]
    """
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
    """Log bot uptime through webhook. If the url is None,
    do nothing.

    :param content: The message to log.
    :type content: str
    :param url: The webhook url to log to.
    :type url: Optional[str]
    """
    if not url:
        return
    webhook = Webhook.from_url(url, adapter=RequestsWebhookAdapter())
    webhook.send(content, username="Starboard Uptime")


def get_intersect(list1: Iterable[Any], list2: Iterable[Any]) -> List[Any]:
    """Get the intersection of two lists.

    :param list1: The first list.
    :type list1: Iterable[Any]
    :param list2: The second list.
    :type list2: Iterable[Any]
    :return: A list of commong values between both lists.
    :rtype: List[Any]
    """
    return [value for value in list1 if value in list2]


def truncate(content: str, max_length: int, truncate_str: str = "...") -> str:
    """Truncates a string to a certain length.

    Args:
        content (str): The string that may need to be truncated.
        max_length (int): The length to truncate the string to.
        truncate_str (str, optional): The string to append to the end if
            truncated. Defaults to "...".

    Returns:
        str: The truncated string.
    """
    if len(content) > max_length:
        content = content[0 : max_length - len(truncate_str)] + truncate_str
    return content


def chunk_list(
    lst: List[Any], max_size: int
) -> Generator[List[Any], None, None]:
    """Take a list and split it into a list of lists
    with a specified size.

    :param lst: The list to chunk
    :type lst: List[Any]
    :param max_size: The maximum size for each resulting list
    :type max_size: int
    :yield: The chunked list
    :rtype: Generator[List[Any], None, None]
    """
    for i in range(0, len(lst), max_size):
        yield lst[i : i + max_size]


def cs_embed(
    changes: Dict[str, Tuple[Any, Any]], bot: "Bot", noticks: bool = False
) -> discord.Embed:
    """Takes a list of changes and generates an embed
    to represent them.

    :param changes: A dictionary of changes, with the original and new value.
    :type changes: Dict[str, Tuple[Any, Any]]
    :param bot: The bot instance.
    :type bot: Bot
    :param noticks: If True, exclude backticks, defaults to False
    :type noticks: bool, optional
    :return: The embed
    :rtype: discord.Embed
    """
    text = cs_text(changes, noticks=noticks)
    return discord.Embed(
        title=t_("Changed Settings:"), description=text, color=bot.theme_color
    )


def cs_text(changes: Dict[str, Tuple[Any, Any]], noticks: bool = False) -> str:
    """Takes a list of changes and generates text to represent them.

    :param changes: A dictionary of changes, with the original and new value.
    :type changes: Dict[str, Tuple[Any, Any]]
    :param noticks: If True, exclude backticks, defaults to False
    :type noticks: bool, optional
    :return: The changes text
    :rtype: str
    """
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
    """Generates a jump link from message id, channel id, and guild id.

    :param message_id: The id of the message
    :type message_id: int
    :param channel_id: The id of the channel
    :type channel_id: int
    :param guild_id: The id of the guild
    :type guild_id: int
    :return: The generated jump link
    :rtype: str
    """
    return (
        f"https://discord.com/channels/{guild_id}/{channel_id}"
        f"/{message_id}"
    )


def escesc(text: str) -> str:
    """Escapes escapes by adding \\ behind any \\.

    :param text: The text to escape in
    :type text: str
    :return: The text with all escapes escaped
    :rtype: str
    """
    text = text.replace("\\", "\\\\")
    return text


def escmd(text: str) -> str:
    """A shortcut to discord.utils.escape_markdown.

    :param text: The text to escape markdown in
    :type text: str
    :return: The text with all markdown escaped
    :rtype: str
    """
    return discord.utils.escape_markdown(text)


def escmask(text: str) -> str:
    """Escapes all link markdown by adding \\ behind "[" and "]".

    :param text: The text to escape links in
    :type text: str
    :return: The text with all links escaped.
    :rtype: str
    """
    text = escesc(text)
    text = text.replace("]", "\\]")
    text = text.replace("[", "\\[")
    return text


def ms(seconds: float) -> float:
    """Converters seconds to milleseconds.

    :param seconds: The seconds to convert
    :type seconds: float
    :return: The seconds in milleseconds
    :rtype: float
    """
    return round(seconds * 1000, 2)


def safe_regex(
    string: str, pattern: str, max_time: float = 0.01
) -> Optional[re.Match]:
    """Runs regex, but with a timeout applied to prevent ReDos.

    :param string: The string to match regex to
    :type string: str
    :param pattern: The regex to match to the strring
    :type pattern: str
    :param max_time: The max time in seconds, defaults to 0.01
    :type max_time: float, optional
    :return: The result of re.search
    :rtype: Optional[re.Match]
    """

    @timeout(seconds=max_time)
    def run_regex(string: str, pattern: str) -> Optional[re.Match]:
        return re.search(pattern, string)

    return run_regex(string, pattern)


def clean_emoji(
    emoji: Union[str, int, discord.Emoji, discord.Reaction]
) -> str:
    """Takes an emoji and converts it to its id or unicode.

    :param emoji: The emoji/emoji name/emoji id/reaction to convert
    :type emoji: Union[str, int, discord.Emoji, discord.Reaction]
    :return: The name of the emoji
    :rtype: str
    """
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
    """Converts a list of emojis to human-readable form.

    :param emojis: The list of emojis to convert.
    :type emojis: List[Union[str, int, discord.Emoji]]
    :param guild: The guild that custom emojis can be found in
    :type guild: discord.Guild
    :return: The list of converterd emojis
    :rtype: List[str]
    """
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
    """Takes a list of emojis, calls convert_emojis, and creates a string
    from the result in human-readable form.

    :param emojis: The list of emojis to convert
    :type emojis: List[Union[str, int, discord.Emoji]]
    :param guild: The guild in which custom emojis can be found
    :type guild: discord.Guild
    :return: The human-readable string
    :rtype: str
    """
    if len(emojis) == 0:
        return t_("None")
    converted = convert_emojis(emojis, guild)
    return " ".join(converted)


def pretty_channel_string(channels: List[int], guild: discord.Guild) -> str:
    """Takes a list of channel ids and joins them by a comma.

    :param channels: The list of channel ids
    :type channels: List[int]
    :param guild: The guild in which the channels can be found
    :type guild: discord.Guild
    :return: The human-readable string
    :rtype: str
    """
    return ", ".join([f"<#{c}>" for c in channels]) or t_("None")


def clean_prefix(ctx: "MyContext") -> str:
    """Cleans up the prefix from a Context.

    :param ctx: The context to clean up the prefix from
    :type ctx: MyContext
    :return: The cleaned up prefix
    :rtype: str
    """
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
    """Similar to clean_prefix, but works without a context.

    :param prefix: The prefix to clean up.
    :type prefix: str
    :param me: The member (or user) object of the bot
    :type me: Union[discord.Member, discord.User]
    :return: The cleaned up prefix.
    :rtype: [type]
    """
    pattern = re.compile(f"<@!?{me.id}>")
    display_name = me.display_name.replace("\\", r"\\")
    return pattern.sub(f"@{display_name}", prefix)
