from app.classes.bot import Bot

from . import qa_events


def setup(bot: Bot):
    qa_events.setup(bot)
