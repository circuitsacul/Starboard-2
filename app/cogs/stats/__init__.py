from app.classes.bot import Bot

from . import bot_block, stats_events


def setup(bot: Bot):
    stats_events.setup(bot)
    bot_block.setup(bot)
