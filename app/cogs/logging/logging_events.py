import datetime

import discord
from discord.ext import commands

from app.classes.bot import Bot


class LoggingEvents(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

        self.type_map = {
            'error': {'color': self.bot.error_color, 'title':  'Error'},
            'info': {'color': self.bot.theme_color, 'title': 'Info'}
        }

    @commands.Cog.listener()
    async def on_guild_log(
        self,
        message: str,
        log_type: str,
        guild: discord.Guild
    ) -> None:
        sql_guild = await self.bot.db.get_guild(guild.id)
        log_channel = guild.get_channel(int(sql_guild['log_channel']))
        if not log_channel:
            return

        embed = discord.Embed(
            title=self.type_map[log_type]['title'],
            description=message,
            color=self.type_map[log_type]['color']
        )
        embed.timestamp = datetime.datetime.utcnow()
        await log_channel.send(embed=embed)


def setup(bot: Bot) -> None:
    bot.add_cog(LoggingEvents(bot))
