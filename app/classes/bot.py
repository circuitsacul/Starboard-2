import asyncio
import io
import json
import logging
import sys
import textwrap
import traceback
from contextlib import redirect_stdout
from typing import List

import discord
import websockets
from discord.ext import commands
from pretty_help import PrettyHelp

from app import checks

from ..cache import Cache
from ..database.database import Database


class Bot(commands.AutoShardedBot):
    def __init__(self, **kwargs):
        self.stats = {}

        self.theme_color = kwargs.pop("theme_color")
        self.dark_theme_color = kwargs.pop("dark_theme_color")
        self.error_color = kwargs.pop("error_color")
        self.db: Database = kwargs.pop("db")
        self.cache: Cache = kwargs.pop("cache")

        self.pipe = kwargs.pop("pipe")
        self.cluster_name = kwargs.pop("cluster_name")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        super().__init__(
            help_command=PrettyHelp(color=self.theme_color),
            command_prefix=self._prefix_callable,
            **kwargs,
            loop=loop,
        )
        self.websocket = None
        self._last_result = None
        self.ws_task = None
        self.responses = asyncio.Queue()
        self.eval_wait = False
        log = logging.getLogger(f"Cluster#{self.cluster_name}")
        log.setLevel(logging.DEBUG)
        log.handlers = [
            logging.FileHandler(
                f"logs/cluster-{self.cluster_name}.log",
                encoding="utf-8",
                mode="a",
            )
        ]

        log.info(
            f'[Cluster#{self.cluster_name}] {kwargs["shard_ids"]}, '
            f'{kwargs["shard_count"]}'
        )
        self.log = log
        self.loop.create_task(self.ensure_ipc())

        self.loop.run_until_complete(self.db.init_database())

        for ext in kwargs.pop("initial_extensions"):
            self.load_extension(ext)

        self.add_check(checks.not_disabled)

        try:
            self.run(kwargs["token"])
        except Exception as e:
            raise e from e
        else:
            sys.exit(-1)

    async def on_message(self, message):
        pass

    async def on_error(self, event: str, *args, **kwargs) -> None:
        _, error, _ = sys.exc_info()
        self.dispatch("log_error", "Error", error, args, kwargs)

    async def _prefix_callable(
        self, bot, message: discord.Message
    ) -> List[str]:
        if message.guild:
            guild = await self.db.get_guild(message.guild.id)
            if not guild:
                prefixes = ["sb!"]
            else:
                prefixes = guild["prefixes"]
        else:
            prefixes = ["sb!"]
        return [f"<@{self.user.id}> ", f"<@!{self.user.id}> "] + prefixes

    def cleanup_code(self, content):
        """Automatically removes code blocks from the code."""
        # remove ```py\n```
        if content.startswith("```") and content.endswith("```"):
            return "\n".join(content.split("\n")[1:-1])

        # remove `foo`
        return content.strip("` \n")

    async def close(self, *args, **kwargs):
        self.log.info("shutting down")
        await self.websocket.close()
        await super().close()

    async def exec(self, code):
        env = {"bot": self, "sys": sys, "_": self._last_result}

        env.update(globals())

        body = self.cleanup_code(code)
        stdout = io.StringIO()

        to_compile = f'async def func():\n{textwrap.indent(body, "  ")}'

        try:
            exec(to_compile, env)
        except Exception as e:
            return f"{e.__class__.__name__}: {e}"

        func = env["func"]
        try:
            with redirect_stdout(stdout):
                ret = await func()
        except Exception:
            value = stdout.getvalue()
            f"{value}{traceback.format_exc()}"
        else:
            value = stdout.getvalue()

            if ret is None:
                if value:
                    return str(value)
                else:
                    return "None"
            else:
                self._last_result = ret
                return f"{value}{ret}"

    async def websocket_loop(self):
        while True:
            try:
                msg = await self.websocket.recv()
            except websockets.ConnectionClosed as exc:
                if exc.code == 1000:
                    return
                raise
            data = json.loads(msg)
            if self.eval_wait and data.get("response"):
                await self.responses.put(data)
            cmd = data.get("command")
            if not cmd:
                continue
            ret = {}
            if cmd == "ping":
                ret = {"response": "pong"}
                self.log.info("received command [ping]")
            elif cmd == "eval":
                self.log.info(f"received command [eval] ({data['content']})")
                content = data["content"]
                data = await self.exec(content)
                ret = {"response": str(data)}
            elif cmd == "set_stats":
                self.log.info("received command [set_stats]")
                self.stats[data["cluster"]] = {
                    "guilds": data["guild_count"],
                    "members": data["member_count"],
                }
                continue
            else:
                ret = {"response": "unknown command"}
            ret["author"] = self.cluster_name
            self.log.info(f"responding: {ret}")
            try:
                await self.websocket.send(json.dumps(ret).encode("utf-8"))
            except websockets.ConnectionClosed as exc:
                if exc.code == 1000:
                    return
                raise

    def _task_done_callback(self, task: asyncio.Task) -> None:
        try:
            task.result()
        except (SystemExit, asyncio.CancelledError):
            pass

    async def ensure_ipc(self):
        self.websocket = w = await websockets.connect("ws://localhost:4000")
        await w.send(self.cluster_name.encode("utf-8"))
        try:
            await w.recv()
            self.ws_task = self.loop.create_task(self.websocket_loop())
            self.ws_task.add_done_callback(self._task_done_callback)
            self.log.info("ws connection succeeded")
        except websockets.ConnectionClosed as exc:
            self.log.warning(
                f"! couldnt connect to ws: {exc.code} {exc.reason}"
            )
            self.websocket = None
            raise
