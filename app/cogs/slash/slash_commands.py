from discord.ext import commands

from app.classes.bot import Bot

# from discord_slash import cog_ext, SlashContext

# import config


class SlashCommands(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self.bot.slash.get_cog_commands(self)

    def cog_unload(self) -> None:
        self.bot.slash.get_cog_commands(self)


def setup(bot: Bot) -> None:
    bot.add_cog(SlashCommands(bot))
