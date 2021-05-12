from typing import Optional

import discord
from aiocache import Cache as MemCache
from aiocache import SimpleMemoryCache

from app import utils
from app.classes.bot import Bot
from app.constants import MISSING


class Cache:
    def __init__(self, bot) -> None:
        self.messages: SimpleMemoryCache = MemCache(
            namespace="messages", ttl=10
        )
        self.bot = bot
        self.users: SimpleMemoryCache = MemCache(namespace="users", ttl=10)

    async def fetch_user(self, user_id: int) -> discord.User:
        cached = await self.users.get(user_id)
        if cached:
            return cached
        user = await self.bot.fetch_user(user_id)
        await self.users.set(user_id, user)
        return user

    async def get_members(
        self, uids: list[int], guild: discord.Guild
    ) -> dict[int, Optional[discord.Member]]:
        await self.bot.wait_until_ready()
        not_found: list[int] = []
        result: dict[int, Optional[discord.Member]] = {}

        for uid in uids:
            cached = guild.get_member(uid)
            if cached:
                result[uid] = cached
            else:
                not_found.append(uid)

        # only query 50 members at a time
        for group in utils.chunk_list(not_found, 50):
            query = await guild.query_members(limit=None, user_ids=group)
            for r in query:
                result[r.id] = r

        return result

    async def fetch_message(
        self, guild_id: int, channel_id: int, message_id: int
    ) -> Optional[discord.Message]:
        cached = await self.messages.get(message_id)
        if not cached:
            guild = self.bot.get_guild(guild_id)
            if not guild:
                return None
            channel = guild.get_channel(channel_id)
            if not channel:
                return None
            try:
                message = await channel.fetch_message(message_id)
            except discord.errors.NotFound:
                message = None
            await self.messages.set(message_id, message or MISSING)
            return message
        return cached if cached is not MISSING else None


def setup(bot: Bot) -> None:
    bot.cache = Cache(bot)
