from app.classes.bot import Bot

from . import base_commands, base_events


def setup(bot: Bot):
    base_commands.setup(bot)
    base_events.setup(bot)
