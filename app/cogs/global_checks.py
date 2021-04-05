from discord.ext import commands

from app import errors
from app.classes.bot import Bot


async def not_disabled(ctx: commands.Context) -> bool:
    if ctx.guild is None:
        return True
    if ctx.channel.permissions_for(ctx.message.author).manage_guild:
        return True
    guild = await ctx.bot.db.guilds.get(ctx.guild.id)
    if not guild["allow_commands"]:
        raise errors.AllCommandsDisabled()
    name = ctx.command.qualified_name
    if name in guild["disabled_commands"]:
        raise errors.CommandDisabled(name)
    return True


async def can_send_messages(ctx: commands.Context) -> bool:
    user = ctx.me
    if not ctx.channel.permissions_for(user).send_messages:
        raise commands.BotMissingPermissions(("Send Messages",))


GLOBAL_CHECKS = [not_disabled, can_send_messages]


def setup(bot: Bot) -> None:
    for check in GLOBAL_CHECKS:
        bot.add_check(check)
