from discord.ext import commands

import config
from app import errors


def is_owner() -> callable:
    async def predicate(ctx: commands.Context) -> bool:
        if ctx.message.author.id not in config.OWNER_IDS:
            raise commands.NotOwner(
                "Only a bot owner can run this command!"
            )
        return True
    return commands.check(predicate)


# Global Checks
async def not_disabled(ctx: commands.Context) -> bool:
    if ctx.channel.permissions_for(ctx.message.author).administrator:
        return True
    guild = await ctx.bot.db.get_guild(ctx.guild.id)
    if not guild['allow_commands']:
        raise errors.AllCommandsDisabled()
    return True
