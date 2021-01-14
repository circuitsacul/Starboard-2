import discord
from discord.ext import commands

from app.classes.bot import Bot


class CacheEvents(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_raw_message_delete(
        self, payload: discord.RawMessageDeleteEvent
    ) -> None:
        queue = self.bot.cache.messages.get_queue(payload.guild_id)
        cached = queue.get(id=payload.message_id)
        if cached:
            print(2)
            queue.remove(cached)

    @commands.Cog.listener()
    async def on_raw_bulk_message_delete(
        self, payload: discord.RawBulkMessageDeleteEvent
    ) -> None:
        queue = self.bot.cache.messages.get_queue(payload.guild_id)
        for mid in payload.message_ids:
            cached = queue.get(id=mid)
            if cached:
                print(1)
                queue.remove(cached)


def setup(bot: Bot) -> None:
    bot.add_cog(CacheEvents(bot))
