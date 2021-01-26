from discord.ext import commands

import config
from app import errors


def is_owner() -> callable:
    async def predicate(ctx: commands.Context) -> bool:
        if ctx.message.author.id not in config.OWNER_IDS:
            raise commands.NotOwner("Only a bot owner can run this command!")
        return True

    return commands.check(predicate)


# Global Checks
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
        raise errors.CommandDisabled(
            f"The command {name} has been disabled "
            "by the moderators of this server."
        )
    return True
