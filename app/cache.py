import discord

from . import queue


class Cache:
    def __init__(self) -> None:
        self.messages = queue.LimitedDictQueue(20)

    def get_message(
        self,
        guild_id: int,
        message_id: int
    ) -> discord.Message:
        queue = self.messages.get_queue(guild_id)
        return queue.get(id=message_id)
