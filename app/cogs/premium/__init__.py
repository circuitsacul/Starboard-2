import typing

from . import p_events

if typing.TYPE_CHECKING:
    from app.classes.bot import Bot


def setup(bot: "Bot"):
    p_events.setup(bot)
