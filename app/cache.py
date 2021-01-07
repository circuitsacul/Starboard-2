from typing import Optional

from . import queue

from .classes.guild import Guild


class Cache:
    def __init__(self) -> None:
        self.guilds = queue.LimitedQueue(500)

    def get_guild(self, guild_id: int) -> Optional[Guild]:
        return self.guilds.get(id=guild_id)
