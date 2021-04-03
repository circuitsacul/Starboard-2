from app.classes.bot import Bot

from . import settings_commands


def setup(bot: Bot):
    settings_commands.setup(bot)
