from discord.ext import commands
from discord_slash import SlashContext, cog_ext

import config
from app.classes.bot import Bot


class SlashCommands(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self.bot.slash.get_cog_commands(self)

    def cog_unload(self) -> None:
        self.bot.slash.get_cog_commands(self)

    @cog_ext.cog_slash(
        name="ping",
        description="See if slash commands are working.",
        guild_ids=config.SLASH_GUILD_IDS,
    )
    async def ping(self, ctx: SlashContext) -> None:
        await ctx.send(content="Pong!")


def setup(bot: Bot) -> None:
    bot.add_cog(SlashCommands(bot))
