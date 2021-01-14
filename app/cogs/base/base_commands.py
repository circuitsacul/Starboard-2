import discord
from discord.ext import commands

from app.utils import ms
from ...classes.bot import Bot


class Base(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    @commands.command(
        name='ping', aliases=['latency'],
        brief="Shows current clusters and shards latency"
    )
    async def ping(self, ctx: commands.Context) -> None:
        cluster = self.bot.cluster_name
        shard = self.bot.get_shard(ctx.guild.shard_id)

        embed = discord.Embed(
            title='Pong!',
            color=self.bot.theme_color
        )
        embed.add_field(
            name=f"Cluster **{cluster}**",
            value=f"{ms(self.bot.latency)} ms",
            inline=False
        )
        embed.add_field(
            name=f"Shard **{shard.id}**",
            value=f"{ms(shard.latency)} ms",
            inline=False
        )
        await ctx.send(embed=embed)


def setup(bot: Bot) -> None:
    bot.add_cog(Base(bot))
