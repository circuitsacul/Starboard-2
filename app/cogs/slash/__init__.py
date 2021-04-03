from app.classes.bot import Bot

from . import slash_commands, slash_events


def setup(bot: Bot):
    slash_commands.setup(bot)
    slash_events.setup(bot)
