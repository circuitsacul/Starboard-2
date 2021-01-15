import discord
from discord.ext import commands

from app.classes.bot import Bot


class LoggingEvents(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_log_error(
        self,
        message: str,
        guild: discord.Guild
    ) -> None:
        sql_guild = await self.bot.db.get_guild(guild.id)
        log_channel = guild.get_channel(int(sql_guild['log_channel']))
        if not log_channel:
            return

        embed = discord.Embed(
            title="Error",
            description=message,
            color=self.bot.error_color
        )
        await log_channel.send(embed=embed)


def setup(bot: Bot) -> None:
    bot.add_cog(LoggingEvents(bot))
