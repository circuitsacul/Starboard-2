import typing

from . import donate_events, p_events

if typing.TYPE_CHECKING:
    from app.classes.bot import Bot


def setup(bot: "Bot"):
    p_events.setup(bot)
    donate_events.setup(bot)
