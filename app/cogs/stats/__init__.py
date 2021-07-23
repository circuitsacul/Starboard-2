from app.classes.bot import Bot

from . import stats_events


def setup(bot: Bot):
    stats_events.setup(bot)
