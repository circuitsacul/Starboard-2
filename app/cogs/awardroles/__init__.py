import typing

from . import ar_commands

if typing.TYPE_CHECKING:
    from app.classes.bot import Bot


def setup(bot: "Bot"):
    ar_commands.setup(bot)
