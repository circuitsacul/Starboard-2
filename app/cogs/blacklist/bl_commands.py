import discord
from discord.ext import commands

from app.classes.bot import Bot
from app import converters
from app import utils
from app import errors


class Blacklist(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    @commands.group(
        name="blacklist",
        aliases=["bl"],
        brief="Lists the channel blacklist for a starboard",
        invoke_without_command=True,
    )
    @commands.guild_only()
    async def blacklist(
        self, ctx: commands.Context, starboard: converters.Starboard
    ) -> None:
        bl_channels = starboard.sql["channel_bl"]
        wl_channels = starboard.sql["channel_wl"]

        wl_string = utils.pretty_channel_string(wl_channels, ctx.guild)
        _bl_string = utils.pretty_channel_string(bl_channels, ctx.guild)
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

    @blacklist.command(
        name="add",
        aliases=["addChannel", "a", "ac"],
        brief="Adds a channel to the blacklist",
    )
    @commands.has_guild_permissions(manage_channels=True)
    async def blacklist_channel(
        self,
        ctx: commands.Context,
        starboard: converters.Starboard,
        channel: discord.TextChannel,
    ) -> None:
        new_bl = starboard.sql["channel_bl"].copy()
        if channel.id in new_bl:
            raise errors.AlreadyExists(
                f"{channel.mention} is already blacklisted on "
                f"{starboard.obj.mention}"
            )
        new_bl.append(channel.id)
        await self.bot.db.starboards.edit(starboard.obj.id, channel_bl=new_bl)
        await ctx.send(
            f"Added {channel.mention} to the blacklist on "
            f"{starboard.obj.mention}."
        )

    @blacklist.command(
        name="remove",
        aliases=["removeChannel", "r", "rc", "del", "d"],
        brief="Removes a channel from the blacklist",
    )
    @commands.has_guild_permissions(manage_channels=True)
    async def unblacklist_channel(
        self,
        ctx: commands.Context,
        starboard: converters.Starboard,
        channel: discord.TextChannel,
    ) -> None:
        new_bl = starboard.sql["channel_wl"].copy()
        if channel.id not in new_bl:
            raise errors.DoesNotExist(
                f"{channel.mention} is not blacklisted on "
                f"{starboard.obj.mention}"
            )
        new_bl.remove(channel.id)
        await self.bot.db.starboards.edit(starboard.obj.id, channel_bl=new_bl)
        await ctx.send(
            f"Removed {channel.mention} from the blacklist on "
            f"{starboard.obj.mention}."
        )

    @blacklist.command(
        name="clear", brief="Removes everything from the blacklist"
    )
    @commands.has_guild_permissions(manage_channels=True)
    async def clear_channel_blacklist(
        self, ctx: commands.Context, starboard: converters.Starboard
    ) -> None:
        await ctx.send("Are you sure?")
        if not await utils.confirm(ctx):
            await ctx.send("Cancelled")
            return

        await self.bot.db.starboards.edit(starboard.obj.id, channel_bl=[])
        await ctx.send(f"Cleared the blacklist for {starboard.obj.mention}.")


def setup(bot: Bot) -> None:
    bot.add_cog(Blacklist(bot))
