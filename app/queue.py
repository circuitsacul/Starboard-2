from typing import Any

from . import errors


class LimitedQueue:
    def __init__(self, max_length: int) -> None:
        self.max_length = max_length
        self.queue = set()

    def clear(self) -> None:
        del self.queue
        self.queue = set()

    def has(self, item: Any) -> bool:
        if item in self.queue:
            return True
        return False

    def add(self, item: Any) -> None:
        self.queue.add(item)
        if len(self.queue) > self.max_length:
            self.queue.pop()

    def remove(self, item: Any) -> None:
        if self.has(item):
            self.queue.remove(item)
        else:
            raise errors.DoesNotExist(
                f"Item {item} not in queue"
            )


class LimitedDictQueue:
    def __init__(self, max_length: int) -> None:
        self.max_length = max_length
        self.queues = {}

    def get_queue(self, key: Any) -> LimitedQueue:
        return self.queues.get(key)

    def del_queue(self, key: Any) -> None:
        queue = self.get_queue(key)
        if queue is None:
            raise errors.DoesNotExist(f"No queue with key {key}")
        del self.queues[key]
        del queue

    def add(self, key: Any, item: Any) -> None:
        queue = self.get_queue(key)
        if queue is None:
            queue = LimitedQueue(self.max_length)
            self.queues[key] = queue
        queue.add(item)

    def remove(self, key: Any, item: Any) -> None:
        queue = self.get_queue(key)
        if queue is None:
            raise errors.DoesNotExist(f"No queue with key {key}")
        queue.remove(item)

    def clear(self) -> None:
        for _, queue in self.queues.items():
            queue.clear()
