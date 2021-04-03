from app.classes.bot import Bot

from . import utility_commands


def setup(bot: Bot):
    utility_commands.setup(bot)
