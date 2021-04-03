from app.classes.bot import Bot

from . import cache, cache_events


def setup(bot: Bot):
    cache_events.setup(bot)
    cache.setup(bot)
