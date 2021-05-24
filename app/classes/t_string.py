class TString:
    def __init__(self, string: str, translate: callable):
        self._value = string
        self._translator = translate

    def __str__(self) -> str:
        """Returns a translated str"""
        return self._translator(self._value)

    def format(self, *args, **kwargs) -> str:
        """Translates and then formats"""
        return str(self).format(*args, **kwargs)

    def __len__(self) -> int:
        """Translates and then calls __len__"""
        return len(str(self))

    def __repr__(self) -> str:
        return f"<TString {self._value}>"
