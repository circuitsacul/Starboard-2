import typing

from . import ar_commands, pr_events, xpr_events

if typing.TYPE_CHECKING:
    from app.classes.bot import Bot


def setup(bot: "Bot"):
    ar_commands.setup(bot)
    xpr_events.setup(bot)
    pr_events.setup(bot)
