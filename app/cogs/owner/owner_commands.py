import io
import textwrap
import time
import traceback
from contextlib import redirect_stdout

import discord
from asyncpg.exceptions import InterfaceError
from discord.ext import commands

from ... import checks, utils, menus
from ...classes.bot import Bot


class Owner(commands.Cog):
    "Owner-only commands"

    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    @commands.command()
    @checks.is_owner()
    async def evall(self, ctx, *, body: str):
        """Evaluates code on all clusters and returns their response"""
        _msgs = await self.bot.websocket.send_command(
            "eval", {"content": body}, expect_resp=True
        )

        msgs = [f"```py\n{m['author']}: {m['data']}\n```" for m in _msgs]

        await ctx.send(" ".join(msgs))

    @commands.command(name="eval")
    @checks.is_owner()
    async def _eval(self, ctx, *, body: str):
        """Evaluates python code on the current cluster"""

        env = {
            "bot": self.bot,
            "ctx": ctx,
            "channel": ctx.channel,
            "author": ctx.author,
            "guild": ctx.guild,
            "message": ctx.message,
            "_": self.bot._last_result,
        }

        env.update(globals())

        body = self.bot.cleanup_code(body)
        stdout = io.StringIO()

        to_compile = f'async def func():\n{textwrap.indent(body, "  ")}'

        try:
            exec(to_compile, env)
        except Exception as e:
            return await ctx.send(f"```py\n{e.__class__.__name__}: {e}\n```")

        func = env["func"]
        try:
            with redirect_stdout(stdout):
                ret = await func()
        except Exception:
            value = stdout.getvalue()
            await ctx.send(f"```py\n{value}{traceback.format_exc()}\n```")
        else:
            value = stdout.getvalue()
            try:
                await ctx.message.add_reaction("\u2705")
            except (discord.Forbidden, discord.NotFound):
                pass

            if ret is None:
                if value:
                    await ctx.send(f"```py\n{value}\n```")
            else:
                self.bot._last_result = ret
                await ctx.send(f"```py\n{value}{ret}\n```")

    @commands.command(name="sqltimes")
    @checks.is_owner()
    async def get_sql_times(
        self, ctx: commands.Context, sort_by: str = "total"
    ) -> None:
        """Shows stats on SQL queries"""
        if sort_by not in ["avg", "total", "exec"]:
            await ctx.send("Valid optons are `avg`, `total`, and `exec`.")
            return

        times = []
        for sql in self.bot.db.sql_times:
            total_time = 0
            executions = 0
            for exec_time in self.bot.db.sql_times[sql]:
                executions += 1
                total_time += exec_time
            times.append(
                (sql, (total_time / executions, total_time, executions))
            )
        pag = commands.Paginator(prefix="", suffix="", max_size=1000)
        if len(times) == 0:
            await ctx.send("Nothing to show")
            return

        def sorter(t):
            if sort_by == "avg":
                return t[1][0]
            elif sort_by == "total":
                return t[1][1]
            elif sort_by == "exec":
                return t[1][2]

        times.sort(key=sorter, reverse=True)
        for sql, exec_time in times:
            pag.add_line(
                f"```{sql}```"
                f"{utils.ms(exec_time[0])} MS AVG | "
                f"{round(exec_time[1], 2)} SECONDS TOTAL | "
                f"{exec_time[2]} EXECUTIONS\n"
            )

        await menus.Paginator(
            embeds=[
                discord.Embed(
                    title="SQL Times",
                    description=p,
                    color=self.bot.theme_color,
                )
                for p in pag.pages
            ],
            delete_after=True,
        ).start(ctx)

    @commands.command(name="restart")
    @checks.is_owner()
    async def restart_bot(self, ctx: commands.Context) -> None:
        """Restars all clusters"""
        if not await menus.Confirm("Restart all clusters?").start(ctx):
            await ctx.send("Cancelled")
            return

        await ctx.send("Restarting...")
        cmd: commands.Command = self.bot.get_command("evall")
        await ctx.invoke(cmd, body="await bot.logout()")

    @commands.command(
        name="runpg",
        aliases=["timepg", "timeit", "runtime"],
        brief="Time postgres queries",
        description="Time postgres queries",
    )
    @checks.is_owner()
    async def time_postgres(self, ctx: commands.Context, *args: list) -> None:
        result = "None"
        times = 1
        runtimes = []

        try:
            async with self.bot.db.pool.acquire() as con:
                async with con.transaction():
                    for a in args:
                        a = "".join(a)
                        try:
                            times = int(a)
                        except Exception:
                            start = time.time()
                            for i in range(0, times):
                                try:
                                    result = await con.fetch(a)
                                except Exception as e:
                                    await ctx.send(e)
                                    raise Exception("rollback")
                            runtimes.append((time.time() - start) / times)
                            times = 1
                    raise Exception("Rollback")
        except (Exception, InterfaceError):
            pass

        for x, r in enumerate(runtimes):
            await ctx.send(f"Query {x} took {round(r*1000, 2)} ms")
        await ctx.send(result[0:500])


def setup(bot: Bot) -> None:
    bot.add_cog(Owner(bot))
