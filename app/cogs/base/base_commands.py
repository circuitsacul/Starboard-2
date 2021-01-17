import discord
from discord.ext import commands

from app.utils import ms
import config

from ...classes.bot import Bot


class Base(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    @commands.command()
    async def test(self, ctx):
        raise Exception('test')

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

    @commands.command(
        name='links', aliases=['invite', 'support'],
        brief="Lists important/useful links"
    )
    async def links(self, ctx: commands.Context) -> None:
        embed = discord.Embed(
            title="Important Links",
            color=self.bot.theme_color
        ).add_field(
            name="Invite Links",
            value=(
                f"**[Support Server]({config.SUPPORT_INVITE})**\n"
                f"**[Invite Starboard]({config.BOT_INVITE})**\n"
            )
        ).add_field(
            name="Vote Links",
            value='\n'.join(config.VOTE_LINKS)
        ).add_field(
            name="Review Links",
            value='\n'.join(config.REVIEW_LINKS)
        )
        await ctx.send(embed=embed)


def setup(bot: Bot) -> None:
    bot.add_cog(Base(bot))
