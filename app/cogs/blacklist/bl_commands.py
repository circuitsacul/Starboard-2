import discord
from discord.ext import commands

from app.classes.bot import Bot
from app import converters
from app import utils


class Blacklist(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    @commands.group(
        name="blacklist",
        aliases=["bl", "wl", "whitelist"],
        brief="Lists the channel blacklist for a starboard",
    )
    @commands.guild_only()
    async def blacklist(
        self, ctx: commands.Context, starboard: converters.Starboard
    ) -> None:
        bl_channels = [
            ctx.guild.get_channel(int(cid))
            for cid in starboard.sql["channel_bl"]
        ]
        wl_channels = [
            ctx.guild.get_channel(int(cid))
            for cid in starboard.sql["channel_wl"]
        ]

        wl_string = (
            utils.pretty_channel_string(wl_channels, ctx.guild)
            or "No Whitelisted Channels Set."
        )
        _bl_string = (
            utils.pretty_channel_string(bl_channels, ctx.guild)
            or "No Blacklisted Channels Set."
        )
        bl_string = (
            _bl_string
            if wl_channels == []
            else _bl_string
            + (
                " (All channels are blacklisted, since "
                "there are whitelisted channels)"
            )
        )

        embed = (
            discord.Embed(
                title=f"Blacklist/Whitelist for {starboard.obj.name}",
                color=self.bot.theme_color,
            )
            .add_field(name="Blacklisted Channels", value=bl_string)
            .add_field(name="Whitelisted Channels", value=wl_string)
        )

        await ctx.send(embed=embed)


def setup(bot: Bot) -> None:
    bot.add_cog(Blacklist(bot))
