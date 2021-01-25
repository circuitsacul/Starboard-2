import discord
from discord.ext import commands

from app.classes.bot import Bot

from . import asc_funcs


class AutoStarEvents(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    @commands.cooldown(5, 10, type=commands.BucketType.channel)
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return
        aschannel = await self.bot.db.get_aschannel(message.channel.id)
        if not aschannel:
            return
        await asc_funcs.handle_message(self.bot, message, aschannel)


def setup(bot: Bot) -> None:
    bot.add_cog(AutoStarEvents(bot))
