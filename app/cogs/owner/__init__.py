from app.classes.bot import Bot

from . import owner_commands


def setup(bot: Bot):
    owner_commands.setup(bot)
