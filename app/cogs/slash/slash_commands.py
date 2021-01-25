import discord
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
        await ctx.send(content="Pong!", complete_hidden=True)

    @commands.command(
        name="slash", brief="Get a link for authorizing slash commands"
    )
    @commands.guild_only()
    async def check_slash(self, ctx: commands.Context) -> None:
        slash_auth = config.SLASH_AUTH + f"&guild_id={ctx.guild.id}"
        embed = discord.Embed(
            title="Slash Commands",
            description=(
                "Try running `/ping` to see if slash commands "
                "are working. If not, a server admin can use "
                f"[this link]({slash_auth}) to give me "
                "the proper permissions."
            ),
            color=self.bot.theme_color,
        )
        await ctx.send(embed=embed)


def setup(bot: Bot) -> None:
    bot.add_cog(SlashCommands(bot))
