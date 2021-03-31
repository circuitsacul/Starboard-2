from app.classes.bot import Bot

from app import checks


def setup(bot: Bot) -> None:
    for check in checks.GLOBAL_CHECKS:
        bot.add_check(check)
