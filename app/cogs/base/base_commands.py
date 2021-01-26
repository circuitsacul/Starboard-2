import discord
from discord.ext import commands

import config
from app.utils import ms

from ...classes.bot import Bot


class Base(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self._about_starboard = (
            "A Starboard is a bot that allows users of a server"
            ' to "vote" to "pin" a message. The main idea is this:\n'
            " - You set a channel as the starboard, typically called "
            "`#starboard`\n"
            " - You set an emoji for voting to pin messages, usually :star:\n"
            " - You set a limit (called requiredStars on this bot) that "
            "tells Starboard how many reactions (of the emoji you set) a "
            "message needs before it is sent to the starboard.\n\n"
            "Once a message reaches the requiredStars limit in  reactions, "
            "Starboard will essentially copy the message and repost it in "
            "your starboard."
        )

    @commands.command(name="about", brief="Explains what a starboard is")
    async def about_starboard(self, ctx: commands.Context) -> None:
        """Explains what a starboard is"""
        embed = discord.Embed(
            title="About Starboard",
            description=self._about_starboard,
            color=self.bot.theme_color,
        )
        await ctx.send(embed=embed)

    @commands.command(
        name="stats", aliases=["botinfo"], brief="Shows bot statistics"
    )
    async def botinfo(self, ctx: commands.Context) -> None:
        """Sends guildCount and memberCount for each
        cluster"""
        clusters = [c for _, c in self.bot.stats.items()]
        total_guilds = sum([c["guilds"] for c in clusters])
        total_members = sum([c["members"] for c in clusters])

        embed = discord.Embed(
            title="Bot Stats",
            description=(
                f"guilds: **{total_guilds}**\n"
                f"users: **{total_members}**\n"
                f"clusters: **{len(clusters)}**\n"
                f"shards: **{self.bot.shard_count}**"
            ),
            color=self.bot.theme_color,
        )
        await ctx.send(embed=embed)

    @commands.command(
        name="ping",
        aliases=["latency"],
        brief="Shows current clusters and shards latency",
    )
    async def ping(self, ctx: commands.Context) -> None:
        """Sends the latency of the current cluster
        and shard."""
        cluster = self.bot.cluster_name
        shard = self.bot.get_shard(ctx.guild.shard_id)

        embed = discord.Embed(title="Pong!", color=self.bot.theme_color)
        embed.add_field(
            name=f"Cluster **{cluster}**",
            value=f"{ms(self.bot.latency)} ms",
            inline=False,
        )
        embed.add_field(
            name=f"Shard **{shard.id}**",
            value=f"{ms(shard.latency)} ms",
            inline=False,
        )
        await ctx.send(embed=embed)

    @commands.command(
        name="links",
        aliases=["invite", "support"],
        brief="Lists important/useful links",
    )
    async def links(self, ctx: commands.Context) -> None:
        """Shows important/useful links"""
        embed = (
            discord.Embed(title="Important Links", color=self.bot.theme_color)
            .add_field(
                name="Discord",
                value=(
                    f"**[Support Server]({config.SUPPORT_INVITE})**\n"
                    f"**[Invite Starboard]({config.BOT_INVITE})**\n"
                ),
                inline=False,
            )
            .add_field(
                name="Support Starboard",
                value=str(
                    "**"
                    + "\n".join(config.DONATE_LINKS)
                    + f"\n[Become a Patron]({config.PATREON_LINK})**"
                ),
            )
            .add_field(
                name="Vote Links",
                value="\n".join(config.VOTE_LINKS),
                inline=False,
            )
            .add_field(
                name="Review Links",
                value="\n".join(config.REVIEW_LINKS),
                inline=False,
            )
        )
        await ctx.send(embed=embed)

    @commands.command(
        name="vote",
        aliases=["votes"],
        brief="View vote links and number of times you've voted",
    )
    async def vote(
        self, ctx: commands.Context, user: discord.User = None
    ) -> None:
        """Shows the number of times you or another user
        has voted, and also lists voting links"""
        user = user or ctx.message.author
        if user.bot:
            await ctx.send(
                f"{user} is a bot. How many times do you "
                "think they've voted?"
            )
            return
        sql_user = await self.bot.db.users.get(user.id)
        if sql_user:
            count = sql_user["votes"]
        else:
            count = 0
        embed = (
            discord.Embed(
                title="Vote for Starboard", color=self.bot.theme_color
            )
            .add_field(
                name="Votes",
                value=f"You have voted **{count}** time"
                f"{'s' if count != 1 else ''}"
                f"{'!' if count != 0 else ' :('}"
                if user.id == ctx.message.author.id
                else f"**{user.name}** has voted **{count}** time"
                f"{'s' if count != 1 else ''}"
                f"{'!' if count != 0 else ' :('}",
                inline=False,
            )
            .add_field(
                name="Vote Links",
                value="\n".join(config.VOTE_LINKS),
                inline=False,
            )
            .add_field(
                name="Review Links",
                value="\n".join(config.REVIEW_LINKS),
                inline=False,
            )
        )
        await ctx.send(embed=embed)


def setup(bot: Bot) -> None:
    bot.add_cog(Base(bot))
