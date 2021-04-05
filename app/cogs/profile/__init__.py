from app.classes.bot import Bot

from . import profile_commands


def setup(bot: Bot):
    profile_commands.setup(bot)
