from typing import Any, Dict, List, Optional, Tuple

import discord
from aiocache import Cache as MemCache
from aiocache import SimpleMemoryCache

from app import utils
from app.classes.bot import Bot
from app.constants import MISSING


def cached(  # for future use
    namespace: str,
    ttl: int,
    *,
    cache_args: Tuple[int] = None,
    cache_kwargs: Tuple[str] = None,
):
    cache: SimpleMemoryCache = MemCache(namespace=namespace, ttl=ttl)

    def get_cache_sig(args: List[Any], kwargs: Dict[Any, Any]) -> List[Any]:
        result = []
        if cache_args:
            result.extend([args[i] for i in cache_args])
        if cache_kwargs:
            result.extend([kwargs.get(k, None) for k in cache_kwargs])
        return result

    def wrapper(coro):
        async def predicate(*args, **kwargs):
            sig = get_cache_sig(args, kwargs)
            cached = await cache.get(sig, default=MISSING)
            if cached is not MISSING:
                return cached

            result = await coro(*args, **kwargs)
            await cache.set(sig, result)
            return result

        return predicate

    return wrapper


class Cache:
    def __init__(self, bot) -> None:
        self.messages: SimpleMemoryCache = MemCache(
            namespace="messages", ttl=30
        )
        self.bot = bot
        self.users: SimpleMemoryCache = MemCache(namespace="users", ttl=15)

    async def fetch_user(self, user_id: int) -> discord.User:
        cached = await self.users.get(user_id, default=MISSING)
        if cached is not MISSING:
            return cached
        try:
            user = await self.bot.fetch_user(user_id)
        except discord.NotFound:
            user = None
        await self.users.set(user_id, user)
        return user

    async def get_members(
        self, uids: List[int], guild: discord.Guild
    ) -> Dict[int, Optional[discord.Member]]:
        await self.bot.wait_until_ready()
        not_found: List[int] = []
        result: Dict[int, Optional[discord.Member]] = {}

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
        cached = await self.messages.get(message_id, default=MISSING)
        if cached is not MISSING:
            return cached

        message = None
        guild = self.bot.get_guild(guild_id)
        if guild:
            channel = guild.get_channel(channel_id)
        if channel:
            try:
                message = await channel.fetch_message(message_id)
            except discord.errors.NotFound:
                pass

        await self.messages.set(message_id, message)
        return message


def setup(bot: Bot) -> None:
    bot.cache = Cache(bot)
