import typing

from . import pr_commands

if typing.TYPE_CHECKING:
    from app.classes.bot import Bot


def setup(bot: "Bot"):
    pr_commands.setup(bot)
