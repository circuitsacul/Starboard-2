from discord.ext import commands, tasks

from app.classes.bot import Bot


class StatsEvents(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self.broadcast_stats.start()

    @tasks.loop(minutes=1)
    async def broadcast_stats(self) -> None:
        await self.bot.wait_until_ready()
        member_count = 0
        for g in self.bot.guilds:
            if g.member_count:
                member_count += g.member_count

        await self.bot.send_command(
            "set_stats",
            {
                "guild_count": len(self.bot.guilds),
                "member_count": member_count,
            },
        )


def setup(bot: Bot) -> None:
    bot.add_cog(StatsEvents(bot))
