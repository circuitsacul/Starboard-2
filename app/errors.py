from discord.ext import commands


# CommandErrors
class ConversionError(commands.CommandError):
    pass


class DoesNotExist(commands.CommandError):
    pass


class AlreadyExists(commands.CommandError):
    pass


# Base Exceptions
class AlreadyStarboardMessage(Exception):
    pass


class AlreadyOrigMessage(Exception):
    pass


# CheckFailures
class AllCommandsDisabled(commands.CheckFailure):
    pass


class CommandDisabled(commands.CheckFailure):
    pass
