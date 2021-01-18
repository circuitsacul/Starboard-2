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
        if not queue:
            return
        cached = queue.get(id=payload.message_id)
        if cached:
            queue.remove(cached)

    @commands.Cog.listener()
    async def on_raw_bulk_message_delete(
        self, payload: discord.RawBulkMessageDeleteEvent
    ) -> None:
        queue = self.bot.cache.messages.get_queue(payload.guild_id)
        if not queue:
            return
        for mid in payload.message_ids:
            cached = queue.get(id=mid)
            if cached:
                queue.remove(cached)

    @commands.Cog.listener()
    async def on_message_edit(
        self, before: discord.Message, after: discord.Message
    ) -> None:
        queue = self.bot.cache.messages.get_queue(after.guild.id)
        if not queue:
            return
        cached = queue.get(id=after.id)
        if cached:
            queue.remove(cached)
            queue.add(after)


def setup(bot: Bot) -> None:
    bot.add_cog(CacheEvents(bot))
