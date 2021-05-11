from discord.ext import commands

import config
from app import errors
from app.classes.context import MyContext


def is_owner() -> callable:
    async def predicate(ctx: "MyContext") -> bool:
        if ctx.message.author.id not in config.OWNER_IDS:
            raise errors.NotOwner()
        return True

    return commands.check(predicate)


def support_server() -> callable:
    async def predicate(ctx: "MyContext") -> bool:
        if not ctx.guild:
            raise errors.NoPrivateMessages()
        if ctx.guild.id != config.ROLE_SERVER:
            raise errors.SupportServerOnly()
        return True

    return commands.check(predicate)
