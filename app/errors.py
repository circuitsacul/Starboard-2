from discord.ext import commands

from app.i18n import t_


# CommandErrors
class ConversionError(commands.CommandError):
    pass


class DoesNotExist(commands.CommandError):
    pass


class AlreadyExists(commands.CommandError):
    pass


class InvalidLocale(commands.CommandError):
    def __init__(self, locale: str) -> None:
        super().__init__(
            t_("{0} is not a valid language code.").format(locale)
        )


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
