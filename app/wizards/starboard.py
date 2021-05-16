from typing import TYPE_CHECKING, Awaitable, Callable

import discord
from discord.ext import commands

from app import converters, errors
from app.i18n import t_
from app.menus import Wizard

if TYPE_CHECKING:
    from app.classes.context import MyContext


class NotAStarboard(commands.TextChannelConverter):
    async def convert(self, ctx: "MyContext", arg: str) -> discord.TextChannel:
        obj = await super().convert(ctx, arg)
        exists = await ctx.bot.db.starboards.get(obj.id)
        if exists:
            raise errors.AlreadyStarboard(obj.mention)
        return obj


def required_stars(arg: str) -> int:
    num = converters.myint(arg)
    if num < 1:
        raise commands.BadArgument(t_("requiredStars cannot be less than 1."))
    elif num > 500:
        raise commands.BadArgument(
            t_("requiredStars cannot be greater than 500.")
        )
    return num


def starboard_wizard(
    done_callback: Callable[[Wizard], Awaitable[None]]
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
        NotAStarboard(),
    )
    w.add_step(
        "Required Stars",
        "required",
        "How many stars should a message need to appear on the starboard?",
        required_stars,
        True,
        3,
    )
    w.add_step(
        "Self Star",
        "self_star",
        "Should users be allowed to star their own messages?",
        converters.mybool,
        True,
        False,
    )
    return w
