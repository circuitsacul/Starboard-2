from app.classes.bot import Bot

from . import leveling_events


def setup(bot: Bot):
    leveling_events.setup(bot)
