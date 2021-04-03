from app.classes.bot import Bot

from . import bl_commands


def setup(bot: Bot):
    bl_commands.setup(bot)
