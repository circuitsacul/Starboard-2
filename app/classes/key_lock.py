from typing import Any, Set


class Locked(Exception):
    def __init__(self):
        super().__init__("Lock is already acquired.")


class KeyLock:
    def __init__(self):
        self.locks: Set[int] = set()

    def acquire(self, key: Any):
        if key in self.locks:
            raise Locked()
        self.locks.add(key)

    def release(self, key: Any):
        if key in self.locks:
            self.locks.remove(key)
