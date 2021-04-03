from app.classes.bot import Bot

from . import asc_commands, asc_events


def setup(bot: Bot):
    asc_commands.setup(bot)
    asc_events.setup(bot)
