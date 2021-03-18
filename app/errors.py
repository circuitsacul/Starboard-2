from discord.ext import commands


class ConversionError(commands.CommandError):
    pass


class DoesNotExist(commands.CommandError):
    pass


class AlreadyExists(commands.CommandError):
    pass


class AlreadyStarboardMessage(Exception):
    pass


class AlreadyOrigMessage(Exception):
    pass


class AllCommandsDisabled(commands.CheckFailure):
    pass


class CommandDisabled(commands.CheckFailure):
    pass
