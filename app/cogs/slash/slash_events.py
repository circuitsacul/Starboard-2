from discord_slash import SlashContext

from app import commands
from app.classes.bot import Bot


class SlashEvents(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_slash_command_error(
        self, ctx: SlashContext, e: Exception
    ) -> None:
        self.bot.dispatch("log_error", "Slash Command Error", e)


def setup(bot: Bot) -> None:
    bot.add_cog(SlashEvents(bot))
