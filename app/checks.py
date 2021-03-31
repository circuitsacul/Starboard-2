from discord.ext import commands

import config


def is_owner() -> callable:
    async def predicate(ctx: commands.Context) -> bool:
        if ctx.message.author.id not in config.OWNER_IDS:
            raise commands.NotOwner("Only a bot owner can run this command!")
        return True

    return commands.check(predicate)
