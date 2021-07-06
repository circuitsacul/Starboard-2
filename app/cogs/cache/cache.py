from typing import Any, Dict, List, Optional, Tuple

import cachetools
import discord

from app import utils
from app.classes.bot import Bot
from app.constants import MISSING


def cached(
    ttl: int,
    maxsize: int,
    *,
    cache_args: Tuple[int] = None,
    cache_kwargs: Tuple[str] = None,
):
    cache = cachetools.TTLCache(maxsize, ttl)

    def get_cache_sig(args: List[Any], kwargs: Dict[Any, Any]) -> Tuple[Any]:
        result = []
        if cache_args:
            result.extend([args[i] for i in cache_args])
        if cache_kwargs:
            result.extend([kwargs.get(k, None) for k in cache_kwargs])
        for x, item in enumerate(result):
            if isinstance(item, list):
                result[x] = tuple(item)
        return tuple(result)

    def wrapper(coro):
        async def predicate(*args, **kwargs):
            sig = get_cache_sig(args, kwargs)
            try:
                return cache[sig]
            except KeyError:
                pass

            result = await coro(*args, **kwargs)
            cache[sig] = result
            return result

        return predicate

    return wrapper


class Cache:
    def __init__(self, bot: "Bot") -> None:
        self.messages = cachetools.TTLCache(5_000, 30)
        self.users = cachetools.TTLCache(5_000, 15)
        self.bot = bot

    async def fetch_user(self, user_id: int) -> discord.User:
        cached = self.users.get(user_id, default=MISSING)
        if cached is not MISSING:
            return cached
        try:
            user = await self.bot.fetch_user(user_id)
        except discord.NotFound:
            user = None
        self.users.setdefault(user_id, user)
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
        cached = self.messages.get(message_id, default=MISSING)
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

        self.messages.setdefault(message_id, message)
        return message


def setup(bot: Bot) -> None:
    bot.cache = Cache(bot)
