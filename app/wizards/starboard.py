from typing import TYPE_CHECKING, Awaitable, Callable, Union

import discord
from discord.ext import commands

from app import converters, errors, utils
from app.i18n import t_
from app.menus import Wizard

if TYPE_CHECKING:
    from app.classes.context import MyContext


class CanBeStarboard(commands.TextChannelConverter):
    async def convert(self, ctx: "MyContext", arg: str) -> discord.TextChannel:
        obj = await super().convert(ctx, arg)
        exists = await ctx.bot.db.starboards.get(obj.id)
        if exists:
            raise errors.AlreadyStarboard(obj.mention)
        is_asc = await ctx.bot.db.aschannels.get(obj.id)
        if is_asc:
            raise errors.CannotBeStarboardAndAutostar()
        return obj


class ListOfEmojis(converters.Emoji):
    async def convert(self, ctx: "MyContext", arg: str) -> list[str]:
        args = [a.strip() for a in arg.split()]
        set_emojis: set[str] = set()
        for arg in args:
            try:
                converted = await super().convert(ctx, arg)
            except Exception:
                continue
            else:
                set_emojis.add(converted)
        emojis: list[str] = []
        for e in set_emojis:
            if isinstance(e, discord.Emoji):
                emojis.append(str(e.id))
            else:
                emojis.append(e)
        return emojis


class Emoji(converters.Emoji):
    async def convert(self, ctx: "MyContext", arg: str) -> str:
        result = await super().convert(ctx, arg)
        if isinstance(result, discord.Emoji):
            return str(result.id)
        return result


def required_stars(arg: str) -> int:
    num = converters.myint(arg)
    if num < 1:
        raise commands.BadArgument(t_("requiredStars cannot be less than 1."))
    elif num > 500:
        raise commands.BadArgument(
            t_("requiredStars cannot be greater than 500.")
        )
    return num


def pretty_emoji_str_list(
    guild: discord.Guild,
) -> Callable[[list[Union[str, discord.Emoji]]], Awaitable[str]]:
    async def predicate(emojis: list[Union[str, discord.Emoji]]) -> str:
        return utils.pretty_emoji_string(emojis, guild)

    return predicate


def pretty_emoji_str(
    guild: discord.Guild,
) -> Callable[[Union[str, discord.Emoji]], Awaitable[str]]:
    async def predicate(emoji: Union[str, discord.Emoji]) -> str:
        return utils.pretty_emoji_string([emoji], guild)

    return predicate


def starboard_wizard(
    done_callback: Callable[[Wizard], Awaitable[None]],
    ctx: "MyContext",
) -> Wizard:
    w = Wizard(
        t_("Starboard Setup Wizard"),
        t_(
            "This will walk you through *some* of the key settings for "
            "a starboard. To edit the rest of the settings, you can use "
            "the commands."
        ),
        done_callback,
    )
    w.add_step(
        "Channel",
        "channel",
        "Please choose a channel to setup a new starboard in.",
        CanBeStarboard(),
    )
    w.add_step(
        "Required Stars",
        "required",
        t_("How many stars should a message need to appear on the starboard?"),
        required_stars,
        True,
        3,
    )
    w.add_step(
        "Self Star",
        "self_star",
        t_("Should users be allowed to star their own messages?"),
        converters.mybool,
        True,
        False,
    )
    w.add_step(
        "Emojis",
        "star_emojis",
        t_(
            'What emojis should count as "stars"? '
            "(These emojis will count towards the points "
            "on a starboard message)"
        ),
        ListOfEmojis(),
        True,
        ["⭐"],
        pretty_emoji_str_list(ctx.guild),
    )
    w.add_step(
        "Display Emoji",
        "display_emoji",
        t_(
            "What emoji should show up next to the "
            "points on a starboard message?"
        ),
        Emoji(),
        True,
        "⭐",
        pretty_emoji_str(ctx.guild),
    )
    return w
