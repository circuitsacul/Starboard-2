import discord
from discord.ext import commands
from discord_slash import SlashContext, cog_ext

import config
from app.classes.bot import Bot
from app.i18n import t_


class SlashCommands(commands.Cog):
    "Slash commands"

    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    @cog_ext.cog_slash(
        name="ping",
        description="See if slash commands are working.",
        guild_ids=config.SLASH_GUILD_IDS,
    )
    async def ping(self, ctx: SlashContext) -> None:
        await ctx.send(content="Pong!", hidden=True)

    @commands.command(
        name="slash", brief="Get a link for authorizing slash commands"
    )
    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    async def check_slash(self, ctx: commands.Context) -> None:
        slash_auth = config.SLASH_AUTH + f"&guild_id={ctx.guild.id}"
        embed = discord.Embed(
            title="Slash Commands",
            description=t_(
                "Try running `/ping` to see if slash commands "
                "are working. If not, a server admin can use "
                "[this link]({slash_auth}) to give me "
                "the proper permissions."
            ).config(slash_auth),
            color=self.bot.theme_color,
        )
        await ctx.send(embed=embed)


def setup(bot: Bot) -> None:
    bot.add_cog(SlashCommands(bot))
