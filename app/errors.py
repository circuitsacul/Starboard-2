from discord.ext import commands


class ConversionError(Exception):
    pass


class DoesNotExist(Exception):
    pass


class AlreadyExists(Exception):
    pass


class AlreadyStarboardMessage(Exception):
    pass


class AlreadyOrigMessage(Exception):
    pass


class AllCommandsDisabled(commands.CheckFailure):
    pass


class CommandDisabled(commands.CheckFailure):
    pass
