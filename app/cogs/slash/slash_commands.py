import discord
from discord.ext import commands
from discord_slash import SlashContext, cog_ext

import config
from app.classes.bot import Bot
from app.classes.context import MyContext
from app.i18n import t_


class SlashCommands(
    commands.Cog,
    description=t_("Slash commands.", True),
):
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
        name="slash",
        help=t_("Get a link for authorizing slash commands.", True),
    )
    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    async def check_slash(self, ctx: "MyContext") -> None:
        slash_auth = config.SLASH_AUTH + f"&guild_id={ctx.guild.id}"
        embed = discord.Embed(
            title="Slash Commands",
            description=t_(
                "Try running `/ping` to see if slash commands "
                "are working. If not, a server admin can use "
                "[this link]({}) to give me "
                "the proper permissions."
            ).format(slash_auth),
            color=self.bot.theme_color,
        )
        await ctx.send(embed=embed)


def setup(bot: Bot) -> None:
    bot.add_cog(SlashCommands(bot))
