from app.classes.bot import Bot

from . import fun_commands


def setup(bot: Bot):
    fun_commands.setup(bot)
