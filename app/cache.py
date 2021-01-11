from typing import Optional

from . import queue


class Cache:
    def __init__(self) -> None:
        self.guilds = queue.LimitedQueue(500)

    def get_guild(self, guild_id: int) -> Optional[dict]:
        return self.guilds.get(id=guild_id)
