from discord.ext import flags
from discord.ext.flags import *  # noqa F401


class FlagCommand(flags.FlagCommand):
    def __init__(self, *args, **kwargs):
        self._help = kwargs.pop("help", None)
        super().__init__(*args, **kwargs)

    @property
    def help(self):
        return str(self._help)

    @help.setter
    def help(self, *args, **kwargs):
        pass


class FlagGroup(flags.FlagGroup):
    def __init__(self, *args, **kwargs):
        self._help = kwargs.pop("help", None)
        super().__init__(*args, **kwargs)

    @property
    def help(self):
        return str(self._help)

    @help.setter
    def help(self, *args, **kwargs):
        pass

    def command(self, *args, **kwargs):
        kwargs.setdefault("cls", FlagCommand)
        return super().command(*args, **kwargs)

    def group(self, *args, **kwargs):
        kwargs.setdefault("cls", FlagGroup)
        return super().group(*args, **kwargs)


def command(*args, **kwargs):
    kwargs.setdefault("cls", FlagCommand)
    return flags.command(*args, **kwargs)


def group(*args, **kwargs):
    kwargs.setdefault("cls", FlagGroup)
    return flags.group(*args, **kwargs)
