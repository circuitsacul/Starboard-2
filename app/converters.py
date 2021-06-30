import re
from typing import Any, Callable, Tuple, Union

import discord
import emoji
from discord.ext.commands.errors import ChannelNotFound, RoleNotFound

import config
from app import commands, errors
from app.classes.bot import Bot
from app.classes.context import MyContext
from app.classes.sql_object import SQLObject
from app.i18n import t_


def myhex(arg: str) -> str:
    arg = arg.replace("#", "").upper()
    try:
        int(arg, 16)
    except ValueError:
        raise commands.BadArgument(
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
    raise commands.BadArgument(
        t_(
            "I couldn't interpret `{0}` as yes or no. Please "
            "pass one of 'yes', 'no', 'true', or 'false'."
        ).format(arg)
    )


def myint(arg: str) -> int:
    try:
        result = int(arg.replace(",", ""))
        return result
    except ValueError:
        raise commands.BadArgument(
            t_(
                "I couldn't interpret `{0}` as an integer (number). "
                "Please pass something like `10` or `2`."
            ).format(arg)
        )


def myfloat(arg: str) -> float:
    try:
        result = float(arg.replace(",", ""))
        return result
    except ValueError:
        raise commands.BadArgument(
            t_(
                "I couldn't interpret `{0}` as a floating-point "
                "number. Please pass something like `10.9` or `6`."
            ).format(arg)
        )


def language(arg: str) -> Tuple[str, str]:
    arg = arg.lower()

    langs = config.LANGUAGE_MAP
    for lang in langs:
        codes = []
        codes.append(lang["code"])
        codes.append(lang["name"])
        codes.extend(lang["aliases"])
        codes = [c.lower() for c in codes]

        if arg in codes:
            return lang["code"], lang["name"]

    raise errors.InvalidLocale(arg)


class OrNone(commands.Converter):
    def __init__(
        self, subconverter: Union[commands.Converter, Callable[[str], Any]]
    ):
        self.subconverter = subconverter

    async def convert(self, ctx: "MyContext", arg: str) -> Any:
        acceptable_nones = ["none", "default"]
        try:
            if isinstance(self.subconverter, commands.Converter):
                result = await self.subconverter.convert(ctx, arg)
            else:
                result = self.subconverter(arg)
            return result
        except Exception:
            if arg.lower() in acceptable_nones:
                return None
            raise


class PartialMessage(commands.PartialMessageConverter):
    async def convert(self, ctx: "MyContext", arg: str):
        if arg.casefold().strip() == "^":
            history = await ctx.channel.history(limit=2).flatten()
            try:
                m = history[-1]
            except IndexError:
                pass
            else:
                return m
        return await super().convert(ctx, arg)


class PartialGuildMessage(PartialMessage):
    async def convert(
        self, ctx: "MyContext", arg: str
    ) -> Union[discord.Message, discord.PartialMessage]:
        m = await super().convert(ctx, arg)
        if m.guild:
            if m.guild != ctx.guild:
                raise commands.MessageNotFound(arg)
        elif m.channel != ctx.channel:
            raise commands.MessageNotFound(arg)
        return m


class Message(commands.MessageConverter):
    async def convert(self, ctx: "MyContext", arg: str) -> discord.Message:
        if arg.casefold().strip() == "^":
            history = await ctx.channel.history(limit=2).flatten()
            try:
                m = history[-1]
            except IndexError:
                pass
            else:
                return m
        return await super().convert(ctx, arg)


class GuildMessage(Message):
    async def convert(self, ctx: "MyContext", arg: str):
        m = await super().convert(ctx, arg)
        if m.guild:
            if m.guild != ctx.guild:
                raise commands.MessageNotFound(arg)
        elif m.channel != ctx.channel:
            raise commands.MessageNotFound(arg)
        return m


class Role(commands.RoleConverter):
    """Same as default role converter, except that it ignores
    @everyone"""

    def __init__(self, allow_default: bool = False):
        self.allow_default = allow_default
        super().__init__()

    async def convert(self, ctx: "MyContext", arg: str) -> discord.Role:
        try:
            role = await super().convert(ctx, arg)
        except RoleNotFound:
            if arg == "default":
                role = ctx.guild.default_role
            else:
                raise
        if role.id == ctx.guild.default_role.id and not self.allow_default:
            raise RoleNotFound(arg)
        return role


class Emoji(commands.Converter):
    async def convert(
        self, ctx: "MyContext", arg: str
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
            if result:
                return result
        else:
            decoded = emoji.demojize(arg)
            search = re.findall(":[^:]+:", decoded)
            if len(search) == 1 and len(search[0]) == len(decoded):
                as_emoji = search[0]
                as_emoji = emoji.emojize(as_emoji)
                if as_emoji in emoji.UNICODE_EMOJI["en"]:
                    return arg

        if emoji_id is not None:
            raise errors.CustomEmojiFromOtherGuild(arg)
        raise errors.NotAnEmoji(arg)


class Starboard(commands.TextChannelConverter):
    async def convert(self, ctx: "MyContext", arg: str) -> SQLObject:
        channel = await super().convert(ctx, arg)
        if channel.guild != ctx.guild:
            raise ChannelNotFound(arg)

        sql_starboard = await ctx.bot.db.starboards.get(channel.id)
        if sql_starboard is None:
            raise errors.NotStarboard(channel.mention)

        return SQLObject(channel, sql_starboard)


class ASChannel(commands.TextChannelConverter):
    async def convert(self, ctx: "MyContext", arg: str) -> SQLObject:
        channel = await super().convert(ctx, arg)
        if channel.guild != ctx.guild:
            raise ChannelNotFound(arg)

        sql_aschannel = await ctx.bot.db.aschannels.get(channel.id)
        if not sql_aschannel:
            raise errors.NotAutoStarChannel(channel.mention)

        return SQLObject(channel, sql_aschannel)


class Command(commands.Converter):
    async def convert(self, ctx: "MyContext", arg: str) -> commands.Command:
        if arg == "_commands":
            raise errors.NotCommand(arg)
        cmd = ctx.bot.get_command(arg)
        if not cmd:
            raise errors.NotCommand(arg)
        return cmd


class CommandOrCog(Command):
    async def convert(
        self, ctx: "MyContext", arg: str
    ) -> Union[commands.Cog, commands.Command]:
        try:
            return await super().convert(ctx, arg)
        except errors.NotCommand:
            pass

        bot: Bot = ctx.bot
        cog = bot.get_cog(arg)
        if cog:
            return cog

        raise errors.CommandCategoryNotFound(arg)


class PermGroup(commands.Converter):
    async def convert(self, ctx: "MyContext", arg: str) -> dict:
        permgroup = await ctx.bot.db.permgroups.get_name(ctx.guild.id, arg)

        if not permgroup:
            raise errors.PermGroupNotFound(arg)

        return permgroup


class PermRole(Role):
    def __init__(self, group_arg_index: int):
        self.group_arg_index = group_arg_index
        super().__init__(allow_default=True)

    async def convert(self, ctx: "MyContext", arg: str) -> SQLObject:
        group = ctx.args[self.group_arg_index]
        role = await super().convert(ctx, arg)

        permrole = await ctx.bot.db.permroles.get(role.id, int(group["id"]))
        if not permrole:
            raise errors.PermRoleNotFound(role.name, group["name"])
        return SQLObject(role, permrole)


class XPRole(Role):
    async def convert(self, ctx: "MyContext", arg: str) -> SQLObject:
        role = await super().convert(ctx, arg)
        xprole = await ctx.bot.db.xproles.get(role.id)
        if not xprole:
            raise errors.XpRoleNotFound(role.name)
        return SQLObject(role, xprole)


class PosRole(Role):
    async def convert(self, ctx: "MyContext", arg: str) -> SQLObject:
        role = await super().convert(ctx, arg)
        posrole = await ctx.bot.db.posroles.get(role.id)
        if not posrole:
            raise errors.PosRoleNotFound(role.name)
        return SQLObject(role, posrole)
