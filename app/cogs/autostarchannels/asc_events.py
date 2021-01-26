import datetime

import discord
from discord.ext import commands

from app.classes.bot import Bot

from . import asc_funcs


class AutoStarEvents(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self.cooldown = commands.CooldownMapping.from_cooldown(
            3, 10, commands.BucketType.channel
        )

    @commands.Cog.listener()
    async def on_guild_channel_delete(
        self, channel: discord.abc.GuildChannel
    ) -> None:
        if not isinstance(channel, discord.TextChannel):
            return
        aschannel = await self.bot.db.aschannels.get(channel.id)
        if not aschannel:
            return
        await self.bot.db.aschannels.delete(channel.id)
        self.bot.dispatch(
            "guild_log",
            (
                f"`{channel.name}` was deleted so I removed that "
                "AutoStarChannel."
            ),
            "info",
            channel.guild,
        )

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return
        aschannel = await self.bot.db.aschannels.get(message.channel.id)
        if not aschannel:
            return

        bucket = self.cooldown.get_bucket(message)
        retry_after = bucket.update_rate_limit(
            message.created_at.replace(
                tzinfo=datetime.timezone.utc
            ).timestamp()
        )
        if retry_after:
            return

        await asc_funcs.handle_message(self.bot, message, aschannel)


def setup(bot: Bot) -> None:
    bot.add_cog(AutoStarEvents(bot))
