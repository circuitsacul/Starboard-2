import io
import textwrap
import time
import traceback
from contextlib import redirect_stdout

import discord
from discord.ext import commands
from jishaku.cog import OPTIONAL_FEATURES, STANDARD_FEATURES
from jishaku.exception_handling import ReplResponseReactor
from jishaku.features.baseclass import Feature

from ... import checks, menus, utils
from ...classes.bot import Bot


class Rollback(Exception):
    pass


class RunSqlConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, arg: str):
        try:
            arg = int(arg)
        except ValueError:
            try:
                prev_arg = int(ctx.args[-1])
            except (IndexError, ValueError, TypeError):
                prev_arg = None
            else:
                ctx.args.pop(-1)
            return (prev_arg or 1, arg)
        else:
            return arg


class Owner(*OPTIONAL_FEATURES, *STANDARD_FEATURES):
    """Owner Only Commands"""

    @Feature.Command(
        name="runpg",
        aliases=["timeit"],
        help="Times postgres queries. Rolls back any changes.",
    )
    async def jsk_runpg(self, ctx: commands.Context, *to_run: RunSqlConverter):
        results: list[str] = []
        times: list[float] = []

        try:
            async with ctx.bot.db.pool.acquire() as con:
                async with con.transaction():
                    async with ReplResponseReactor(ctx.message):
                        with self.submit(ctx):
                            for count, sql in to_run:
                                _times: list[float] = []
                                r = None
                                for _ in range(0, count):
                                    s = time.perf_counter()
                                    r = await con.fetch(sql)
                                    _times.append(time.perf_counter() - s)
                                results.append(r if r else [None])
                                times.append(sum(_times) / len(_times))
                    raise Rollback
        except Rollback:
            pass

        message = "\n".join(
            [
                f"Query {n} to {round(t*1000, 3)}ms.\n - "
                + "\n - ".join([str(r) for r in results[n]])
                for n, t in enumerate(times)
            ]
        )
        paginator = commands.Paginator(max_size=1985)
        for line in message.split("\n"):
            paginator.add_line(line)
        pages = [
            p + f"{n}/{len(paginator.pages)}"
            for n, p in enumerate(paginator.pages, 1)
        ]
        await menus.Paginator(text=pages, delete_after=True).start(ctx)

    @Feature.Command(name="evall", help="Runs code on all clusters.")
    async def evall(self, ctx, *, body: str):
        async with ReplResponseReactor(ctx.message):
            with self.submit(ctx):
                _msgs = await self.bot.websocket.send_command(
                    "eval", {"content": body}, expect_resp=True
                )

        msgs = "\n".join([f"{m['author']}: {m['data']}" for m in _msgs])
        pag = commands.Paginator(max_size=1985, prefix="```py")
        for line in msgs.split("\n"):
            pag.add_line(line)
        pages = [
            p + f"{n}/{len(pag.pages)}" for n, p in enumerate(pag.pages, 1)
        ]

        await menus.Paginator(text=pages, delete_after=True).start(ctx)

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
                f"```sql\n{sql}```"
                f"{utils.ms(exec_time[0])} MS AVG | "
                f"{round(exec_time[1], 2)} SECONDS TOTAL | "
                f"{exec_time[2]} EXECUTIONS\n"
            )

        await menus.Paginator(
            text=[
                p + f"{n}/{len(pag.pages)}" for n, p in enumerate(pag.pages, 1)
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
        await self.bot.websocket.send_command("restart", {}, expect_resp=False)


def setup(bot: Bot) -> None:
    bot.add_cog(Owner(bot=bot))
