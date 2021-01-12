import re

import discord
from discord.ext import commands, flags

from . import errors
from .classes.sql_object import SQLObject


def mybool(arg: str) -> bool:
    yes = [
        'y', 'yes', 'on', 'enabled', 'enable', 'true', 't'
    ]
    no = [
        'n', 'no', 'off', 'disabled', 'disable', 'false', 'f'
    ]

    if arg.lower() in yes:
        return True
    elif arg.lower() in no:
        return False
    raise flags.ArgumentParsingError(
        f"I couldn't interpret `{arg}` as yes or no. Please "
        "pass one of 'yes', 'no', 'true', or 'false'."
    )


def myint(arg: str) -> int:
    try:
        result = int(arg)
        return result
    except ValueError:
        raise flags.ArgumentParsingError(
            f"I couldn't interpret `{arg}` as an integer (number). "
            "Please pass something like `10` or `2`"
        )


def myfloat(arg: str) -> float:
    try:
        result = float(arg)
        return result
    except ValueError:
        raise flags.ArgumentParsingError(
            f"I couldn't interpret `{arg}` as a floating-point "
            "number. Please pass something like `10.9` or `6`."
        )


class Starboard(commands.Converter):
    async def convert(
        self,
        ctx: commands.Context,
        arg: str
    ) -> SQLObject:
        mention_pattern = "^<#[0-9]+>$"
        digit_pattern = '^[0-9][0-9]*[0-9]$'

        channel_id = None

        by_name = discord.utils.get(ctx.guild.channels, name=arg)
        if by_name is not None:
            channel_id = by_name.id
        elif re.match(mention_pattern, arg):
            channel_id = int(arg[2:-1])
        elif re.match(digit_pattern, arg):
            channel_id = int(arg)

        if channel_id is None:
            raise commands.errors.ChannelNotFound(arg)

        channel = ctx.guild.get_channel(channel_id)
        if channel is None:
            raise commands.errors.ChannelNotFound(arg)

        sql_starboard = await ctx.bot.db.get_starboard(channel_id)
        if sql_starboard is None:
            raise errors.DoesNotExist(
                f"{channel.mention} is not a starboard."
            )

        return SQLObject(channel, sql_starboard)
