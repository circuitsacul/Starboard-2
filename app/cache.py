from . import queue


class Cache:
    def __init__(self) -> None:
        self.messages = queue.LimitedDictQueue(1000)
        self.guilds = queue.LimitedQueue(500)
