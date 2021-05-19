import inspect
from typing import List, Union

import discord
from discord.ext import commands

from app.i18n import t_


# Custom CommandErrors
class SupportServerOnly(commands.BadArgument):
    def __init__(self):
        super().__init__()


class XpRoleAlreadyExists(commands.BadArgument):
    def __init__(self, role: str):
        message = t_("{0} is already an XPRole.").format(role)
        super().__init__(message=message)


class XpRoleNotFound(commands.BadArgument):
    def __init__(self, role: str):
        message = t_("{0} is not a XPRole.").format(role)
        super().__init__(message=message)


class PermRoleAlreadyExists(commands.BadArgument):
    def __init__(self, role: str, group: str):
        message = t_(
            "**{0}** is already a PermRole on the PermGroup **{1}**."
        ).format(role, group)
        super().__init__(message=message)


class PermRoleNotFound(commands.BadArgument):
    def __init__(self, role: str, group: str):
        message = t_(
            "**{0}** is not a PermRole on the PermGroup **{1}**."
        ).format(role, group)
        super().__init__(message=message)


class PermGroupNotFound(commands.BadArgument):
    def __init__(self, arg: str):
        message = t_(
            "I couldn't find any PermGroups with the name **{0}**."
        ).format(arg)
        super().__init__(message=message)


class GroupNameAlreadyExists(commands.BadArgument):
    def __init__(self, arg: str):
        message = t_(
            "**{0}** is already the name of another PermGroup."
        ).format(arg)
        super().__init__(message=message)


class NotAnEmoji(commands.BadArgument):
    def __init__(self, arg: str):
        message = t_("{0} is not an emoji.").format(arg)
        super().__init__(message=message)


class CustomEmojiFromOtherGuild(commands.BadArgument):
    def __init__(self, arg: Union[str, discord.Emoji]):
        message = t_(
            "{0} is an emoji, but from another server. "
            "Please pass a default emoji or a custom emoji "
            "from this server."
        ).format(arg)
        super().__init__(message=message)


class NotStarboard(commands.BadArgument):
    def __init__(self, arg: str):
        message = t_("The channel {0} is not a starboard.").format(arg)
        super().__init__(message=message)


class NotCommand(commands.BadArgument):
    def __init__(self, arg: str):
        message = t_("`{0}` is not a valid command.").format(arg)
        super().__init__(message=message)


class CommandCategoryNotFound(commands.BadArgument):
    def __init__(self, arg: str):
        message = t_("`{0}` is not a valid command or category.").format(arg)
        super().__init__(message=message)


class NotAutoStarChannel(commands.BadArgument):
    def __init__(self, arg: str):
        message = t_("The channel {0} is not an AutoStar channel.").format(arg)
        super().__init__(message=message)


class NotASEmoji(commands.BadArgument):
    def __init__(self, emoji: str, aschannel: str):
        message = t_(
            "{0} is not an emoji on the AutoStar channel {1}."
        ).format(emoji, aschannel)
        super().__init__(message=message)


class AlreadyASEmoji(commands.BadArgument):
    def __init__(self, emoji: str, aschannel: str):
        message = t_(
            "{0} is already an emoji on the AutoStar channel {1}."
        ).format(emoji, aschannel)
        super().__init__(message=message)


class NotSBEmoji(commands.BadArgument):
    def __init__(self, emoji: str, starboard: str):
        message = t_("{0} is not an emoji on the starboard {1}.").format(
            emoji, starboard
        )
        super().__init__(message=message)


class AlreadySBEmoji(commands.BadArgument):
    def __init__(self, emoji: str, starboard: str):
        message = t_("{0} is already an emoji on the starboard {1}.").format(
            emoji, starboard
        )
        super().__init__(message=message)


class NotBlacklisted(commands.BadArgument):
    def __init__(self, channel: str, starboard: str):
        message = t_("{0} is not blacklisted on {1}.").format(
            channel, starboard
        )
        super().__init__(message=message)


class AlreadyBlacklisted(commands.BadArgument):
    def __init__(self, channel: str, starboard: str):
        message = t_("{0} is already blacklisted on {1}.").format(
            channel, starboard
        )
        super().__init__(message=message)


class NotWhitelisted(commands.BadArgument):
    def __init__(self, channel: str, starboard: str):
        message = t_("{0} is not whitelisted on {1}.").format(
            channel, starboard
        )
        super().__init__(message=message)


class AlreadyWhitelisted(commands.BadArgument):
    def __init__(self, channel: str, starboard: str):
        message = t_("{0} is already whitelisted on {1}.").format(
            channel, starboard
        )
        super().__init__(message=message)


class InvalidLocale(commands.BadArgument):
    def __init__(self, locale: str) -> None:
        super().__init__(
            t_("{0} is not a valid language code.").format(locale)
        )


class MessageNotInDatabse(commands.BadArgument):
    def __init__(self):
        message = t_("That message does not exist in the database.")
        super().__init__(message=message)


class NotDisabled(commands.BadArgument):
    def __init__(self, arg: str):
        message = t_("The command `{0}` is not disabled.").format(arg)
        super().__init__(message=message)


class AlreadyStarboard(commands.BadArgument):
    def __init__(self, arg: str):
        message = t_("{0} is already a starboard.").format(arg)
        super().__init__(message=message)


class AlreadyDisabled(commands.BadArgument):
    def __init__(self, arg: str):
        message = t_("The command `{0}` is already disabled.").format(arg)
        super().__init__(message=message)


class AlreadyQuickAction(commands.BadArgument):
    def __init__(self):
        message = t_("That emoji is already used for another QuickAction")
        super().__init__(message=message)


class AlreadyPrefix(commands.BadArgument):
    def __init__(self, arg: str):
        message = t_("{0} is already a prefix.").format(arg)
        super().__init__(message=message)


class CannotBeStarboardAndAutostar(commands.BadArgument):
    def __init__(self):
        message = t_(
            "A channel cannot be both a starboard and an AutoStar channel"
        )
        super().__init__(message=message)


# Subclassed CommandErrors
class MessageNotFound(commands.BadArgument):
    def __init__(self, argument: str):
        self.argument = argument
        super().__init__(t_("Message {0} not found.").format(argument))

    @classmethod
    def from_original(cls, exc: commands.MessageNotFound):
        return cls(exc.argument)


class MissingRequiredArgument(commands.UserInputError):
    def __init__(self, param: inspect.Parameter):
        self.param = param
        super().__init__(
            t_("**{0}** is a required argument that you didn't pass.").format(
                param.name
            )
        )

    @classmethod
    def from_original(cls, exc: commands.MissingRequiredArgument):
        return cls(exc.param)


class ChannelNotFound(commands.BadArgument):
    def __init__(self, argument: str):
        self.argument = argument
        super().__init__(t_("Channel {0} not found.").format(argument))

    @classmethod
    def from_original(cls, exc: commands.ChannelNotFound):
        return cls(exc.argument)


class ChannelNotReadable(commands.BadArgument):
    def __init__(self, argument: str):
        self.argument = argument
        super().__init__(t_("I can't read messages in {0}.").format(argument))

    @classmethod
    def from_original(cls, exc: commands.ChannelNotReadable):
        return cls(exc.argument)


class RoleNotFound(commands.BadArgument):
    def __init__(self, argument: str):
        self.arugment = argument
        super().__init__(t_("Role {0} not found.").format(argument))

    @classmethod
    def from_original(cls, exc: commands.RoleNotFound):
        return cls(exc.argument)


class UserNotFound(commands.BadArgument):
    def __init__(self, argument: str):
        self.argument = argument
        super().__init__(t_("User {0} not found.").format(argument))

    @classmethod
    def from_original(cls, exc: commands.UserNotFound):
        return cls(exc.argument)


class CommandOnCooldown(commands.CommandError):
    def __init__(self, cooldown, retry_after):
        self.cooldown = cooldown
        self.retry_after = retry_after
        super().__init__(
            t_("You are on cooldown. Try again in {0}s.").format(
                round(retry_after, 2)
            )
        )

    @classmethod
    def from_original(cls, exc: commands.CommandOnCooldown):
        return cls(exc.cooldown, exc.retry_after)


class ExpectedClosingQuoteError(commands.ArgumentParsingError):
    def __init__(self, close_quote: str):
        self.close_quote = close_quote
        super().__init__(t_("Expected closing {0}.").format(close_quote))

    @classmethod
    def from_original(cls, exc: commands.ExpectedClosingQuoteError):
        return cls(exc.close_quote)


# Base Exceptions
class AlreadyStarboardMessage(Exception):
    pass


class AlreadyOrigMessage(Exception):
    pass


class NotInDatabase(Exception):
    pass


# Custom CheckFailures
class AllCommandsDisabled(commands.CheckFailure):
    pass


class CommandDisabled(commands.CheckFailure):
    def __init__(self, arg: str):
        message = t_(
            "The command `{0}` has been disabled by "
            "the moderators of this server."
        ).format(arg)
        super().__init__(message=message)


class CannotUseCommands(commands.CheckFailure):
    pass


# Subclassed CheckFailures
class BotMissingPermissions(commands.CheckFailure):
    def __init__(self, missing_perms: List[str]):
        self.missing_perms = missing_perms

        missing = [
            perm.replace("_", " ").replace("guild", "server").title()
            for perm in missing_perms
        ]

        fmt = ", ".join(missing)

        message = t_(
            "Bot requires the following permissions to "
            "run this command:\n{0}"
        ).format(fmt)
        super().__init__(message)

    @classmethod
    def from_original(cls, exc: commands.BotMissingPermissions):
        return cls(exc.missing_perms)


class NoPrivateMessages(commands.CheckFailure):
    def __init__(self):
        super().__init__(
            t_("This command cannot be used in private messages.")
        )

    @classmethod
    def from_original(cls, exc: commands.NoPrivateMessage):
        return cls()


class NotOwner(commands.CheckFailure):
    def __init__(self):
        super().__init__(t_("This command can only be used by the bot owner."))

    @classmethod
    def from_original(cls, exc: commands.NotOwner):
        return cls()


ERROR_MAP = {
    "MissingRequiredArgument": MissingRequiredArgument,
    "MessageNotFound": MessageNotFound,
    "ChannelNotFound": ChannelNotFound,
    "ChannelNotReadable": ChannelNotReadable,
    "RoleNotFound": RoleNotFound,
    "UserNotFound": UserNotFound,
    "CommandOnCooldown": CommandOnCooldown,
    "ExpectedClosingQuoteError": ExpectedClosingQuoteError,
    "BotMissingPermissions": BotMissingPermissions,
    "NoPrivateMessages": NoPrivateMessages,
    "NotOwner": NotOwner,
}


def convert_error(exc: Exception) -> Exception:
    name = str(exc.__class__.__name__)
    if name in ERROR_MAP:
        exc = ERROR_MAP[name].from_original(exc)

    return exc
