import discord
from discord.ext import commands

from ... import utils
from ...classes.bot import Bot


class OwnerCommands(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    @commands.command(name='sqltimes')
    @commands.is_owner()
    async def get_sql_times(self, ctx: commands.Context) -> None:
        times = []
        for sql in self.bot.db.sql_times:
            total_time = 0
            executions = 0
            for time in self.bot.db.sql_times[sql]:
                executions += 1
                total_time += time
            times.append((sql, (total_time/executions, total_time, executions)))
        pag = commands.Paginator(prefix='', suffix='', max_size=500)
        if len(times) == 0:
            await ctx.send("Nothing to show")
            return
        times.sort(key=lambda t: t[1][1], reverse=True)
        for sql, time in times:
            pag.add_line(
                f"```{sql}```"
                f"{utils.ms(time[0])} MS AVG | "
                f"{round(time[1], 2)} SECONDS TOTAL | "
                f"{time[2]} EXECUTIONS\n"
            )
        await utils.paginator(
            ctx, [
                discord.Embed(
                    title="SQL Times",
                    description=p,
                    color=self.bot.theme_color
                ) for p in pag.pages
            ]
        )

    @commands.command(name='restart')
    @commands.is_owner()
    async def restart_bot(
        self,
        ctx: commands.Context
    ) -> None:
        await ctx.send("Restart all clusters?")
        if await utils.confirm(ctx):
            await ctx.send("Restarting...")
            cmd: commands.Command = self.bot.get_command('evall')
            await ctx.invoke(cmd, body='await bot.logout()')
            return
        await ctx.send("Cancelled")


def setup(bot: Bot) -> None:
    bot.add_cog(OwnerCommands(bot))
