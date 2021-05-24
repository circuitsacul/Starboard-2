from discord.ext import commands
from discord.ext.commands import *  # noqa F401


class Command(commands.Command):
    def __init__(self, *args, **kwargs):
        self._help = kwargs.pop("help", None)
        super().__init__(*args, **kwargs)

    @property
    def help(self):
        return str(self._help)

    @help.setter
    def help(self, *args, **kwargs):
        pass


class Group(commands.Group):
    def __init__(self, *args, **kwargs):
        self._help = kwargs.pop("help", None)
        super().__init__(*args, **kwargs)

    def command(self, *args, **kwargs):
        kwargs.setdefault("cls", Command)
        return super().command(*args, **kwargs)

    def group(self, *args, **kwargs):
        kwargs.setdefault("cls", Group)
        return super().group(*args, **kwargs)

    @property
    def help(self):
        return str(self._help)

    @help.setter
    def help(self, *args, **kwargs):
        pass


class Cog(commands.Cog):
    @property
    def description(self):
        return str(self.__cog_description__)

    @description.setter
    def description(self, desc):
        self.__cog_description__ = desc


def command(*args, **kwargs):
    kwargs.setdefault("cls", Command)
    return commands.command(*args, **kwargs)


def group(*args, **kwargs):
    kwargs.setdefault("cls", Group)
    return commands.group(*args, **kwargs)
