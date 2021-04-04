import re
from typing import Union

import discord
import emoji
from discord.ext import commands, flags

from app.i18n import t_

from . import errors
from .classes.sql_object import SQLObject


def myhex(arg: str) -> str:
    arg = arg.replace("#", "").upper()
    try:
        int(arg, 16)
    except ValueError:
        raise flags.ArgumentParsingError(
            t_(
                "I couldn't interpret `{0}` as a hex value. "
                "Please pass something like `#FFE16C`."
            ).format(arg)
        )
    return arg


def mybool(arg: str) -> bool:
    yes = ["y", "yes", "on", "enabled", "enable", "true", "t"]
    no = ["n", "no", "off", "disabled", "disable", "false", "f"]

    if arg.lower() in yes:
        return True
    elif arg.lower() in no:
        return False
    raise flags.ArgumentParsingError(
        t_(
            "I couldn't interpret `{0}` as yes or no. Please "
            "pass one of 'yes', 'no', 'true', or 'false'."
        ).format(arg)
    )


def myint(arg: str) -> int:
    try:
        result = int(arg)
        return result
    except ValueError:
        raise flags.ArgumentParsingError(
            t_(
                "I couldn't interpret `{0}` as an integer (number). "
                "Please pass something like `10` or `2`."
            ).format(arg)
        )


def myfloat(arg: str) -> float:
    try:
        result = float(arg)
        return result
    except ValueError:
        raise flags.ArgumentParsingError(
            t_(
                "I couldn't interpret `{0}` as a floating-point "
                "number. Please pass something like `10.9` or `6`."
            ).format(arg)
        )


class Emoji(commands.Converter):
    async def convert(
        self, ctx: commands.Context, arg: str
    ) -> Union[discord.Emoji, str]:
        animated_pattern = "^<:.*:[0-9]+>$"
        custom_pattern = "^<a:.*:[0-9]+>$"

        emoji_id = None
        if re.match(animated_pattern, arg):
            emoji_id = int(arg.split(":")[-1][:-1])
        elif re.match(custom_pattern, arg):
            emoji_id = int(arg.split(":")[-1][:-1])

        if emoji_id is not None:
            result = discord.utils.get(ctx.guild.emojis, id=int(emoji_id))
            return result
        elif arg in emoji.UNICODE_EMOJI["en"]:
            return arg

        if emoji_id is not None:
            raise errors.CustomEmojiFromOtherGuild(arg)
        raise errors.NotAnEmoji(arg)


class Starboard(commands.TextChannelConverter):
    async def convert(self, ctx: commands.Context, arg: str) -> SQLObject:
        channel = await super().convert(ctx, arg)

        sql_starboard = await ctx.bot.db.starboards.get(channel.id)
        if sql_starboard is None:
            raise errors.NotStarboard(channel.mention)

        return SQLObject(channel, sql_starboard)


class ASChannel(commands.TextChannelConverter):
    async def convert(self, ctx: commands.Context, arg: str) -> SQLObject:
        channel = await super().convert(ctx, arg)

        sql_aschannel = await ctx.bot.db.aschannels.get(channel.id)
        if not sql_aschannel:
            raise errors.NotAutoStarChannel(channel.mention)

        return SQLObject(channel, sql_aschannel)


class Command(commands.Converter):
    async def convert(
        self, ctx: commands.Context, arg: str
    ) -> commands.Command:
        cmd = ctx.bot.get_command(arg)
        if not cmd:
            raise errors.NotCommand(arg)
        return cmd
