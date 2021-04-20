import typing

from . import donate_events, patreon_events, premium_events

if typing.TYPE_CHECKING:
    from app.classes.bot import Bot


def setup(bot: "Bot"):
    patreon_events.setup(bot)
    donate_events.setup(bot)
    premium_events.setup(bot)
