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

        # If we make it to this point, the emoji doesn't exist

        if emoji_id is not None:
            # Means that the emoji is a custom emoji from another server
            raise errors.DoesNotExist(
                t_(
                    "It looks like `{0}` is a custom emoji, but "
                    "from another server. We can only add custom emojis "
                    "from this server."
                ).format(arg)
            )
        # Just isn't emojis
        raise errors.DoesNotExist(
            t_("I could not interpret `{0}` as an emoji.").format(arg)
        )


class MessageLink(commands.MessageConverter):
    async def convert(self, ctx: commands.Context, arg: str) -> None:
        if arg == "^":
            try:
                message = (await ctx.channel.history(limit=2).flatten())[1]
            except discord.Forbidden:
                raise discord.Forbidden(
                    t_(
                        "I can't read the message history of this channel, "
                        "so I don't know what message you want me to force."
                    )
                )
        else:
            try:
                message = await super().convert(ctx, arg)
            except commands.MessageNotFound as e:
                raise discord.InvalidArgument(
                    t_(
                        "I couldn't find the message `{0}`. "
                        "Please make sure that the message link/id is valid, "
                        "and that it is in this server."
                    ).format(e.argument)
                )
            except commands.ChannelNotFound as e:
                raise discord.InvalidArgument(
                    t_(
                        "I couldn't find the channel `{0}`. "
                        "Please make sure the message link/id is valid, "
                        "and that it is in this server."
                    ).format(e.argument)
                )
            except commands.ChannelNotReadable as e:
                raise discord.Forbidden(
                    t_("I can't read messages in the channel `{0}`.").format(
                        e.argument
                    )
                )
        return message


class Starboard(commands.Converter):
    async def convert(self, ctx: commands.Context, arg: str) -> SQLObject:
        mention_pattern = "^<#[0-9]+>$"
        digit_pattern = "^[0-9][0-9]*[0-9]$"

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

        sql_starboard = await ctx.bot.db.starboards.get(channel_id)
        if sql_starboard is None:
            raise errors.DoesNotExist(
                t_("{0} is not a starboard.").format(channel.mention)
            )

        return SQLObject(channel, sql_starboard)


class ASChannel(commands.TextChannelConverter):
    async def convert(self, ctx: commands.Context, arg: str) -> SQLObject:
        channel = await super().convert(ctx, arg)

        sql_aschannel = await ctx.bot.db.aschannels.get(channel.id)
        if not sql_aschannel:
            raise errors.DoesNotExist(
                t_("{0} is not an AutoStar channel.").format(channel.mention)
            )

        return SQLObject(channel, sql_aschannel)


class Command(commands.Converter):
    async def convert(
        self, ctx: commands.Context, arg: str
    ) -> commands.Command:
        cmd = ctx.bot.get_command(arg)
        if not cmd:
            raise errors.DoesNotExist(
                t_("No commands called `{0}` found.").format(arg)
            )
        return cmd
