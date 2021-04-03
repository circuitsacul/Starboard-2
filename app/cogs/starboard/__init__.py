from app.classes.bot import Bot

from . import starboard_commands, starboard_events


def setup(bot: Bot):
    starboard_commands.setup(bot)
    starboard_events.setup(bot)
