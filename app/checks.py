from typing import Literal

import config
from app import commands, errors
from app.classes.context import MyContext


def is_owner():
    async def predicate(ctx: "MyContext") -> Literal[True]:
        if ctx.message.author.id not in config.OWNER_IDS:
            raise errors.NotOwner()
        return True

    return commands.check(predicate)


def support_server():
    async def predicate(ctx: "MyContext") -> Literal[True]:
        if not ctx.guild:
            raise errors.NoPrivateMessages()
        if ctx.guild.id != config.ROLE_SERVER:
            raise errors.SupportServerOnly()
        return True

    return commands.check(predicate)


def premium_guild():
    async def predicate(ctx: "MyContext") -> Literal[True]:
        if not ctx.guild:
            raise errors.NoPrivateMessages()
        sql_guild = await ctx.bot.db.guilds.get(ctx.guild.id)
        if sql_guild is None or sql_guild["premium_end"] is None:
            raise errors.NoPremium()
        return True

    return commands.check(predicate)
