from typing import Any, List, SupportsIndex, Union


class LimitedList:
    def __init__(self, limit: int = None):
        self._values: List[Any] = []
        self.limit = limit

    def append(self, value: Any):
        self._values.append(value)
        if self.limit and self.limit < len(self):
            self._values = self._values[-self.limit :]

    def pop(self, index: int = 0):
        return self._values.pop(index)

    def remove(self, value: Any):
        return self._values.remove(value)

    def __len__(self):
        return self._values.__len__()

    def __iter__(self):
        return self._values.__iter__()

    def __repr__(self):
        return self._values.__repr__()

    def __str__(self):
        return self._values.__str__()

    def __getitem__(self, i_or_s: Union[SupportsIndex, slice]):
        return self._values.__getitem__(i_or_s)
