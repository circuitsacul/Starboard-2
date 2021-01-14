from typing import Optional

import discord

from . import queue


class Cache:
    def __init__(self) -> None:
        self.messages = queue.LimitedDictQueue(20)

    def get_message(
        self,
        guild_id: int,
        message_id: int
    ) -> Optional[discord.Message]:
        queue = self.messages.get_queue(guild_id)
        if not queue:
            return None
        return queue.get(id=message_id)

    async def fetch_message(
        self,
        bot,
        guild_id: int,
        channel_id: int,
        message_id: int
    ) -> discord.Message:
        cached = self.get_message(guild_id, message_id)
        if not cached:
            guild = bot.get_guild(guild_id)
            channel = guild.get_channel(channel_id)
            try:
                message = await channel.fetch_message(message_id)
            except discord.errors.NotFound:
                return None
            self.messages.add(guild.id, message)
            return message
        return cached
