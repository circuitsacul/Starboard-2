import asyncio
import io
import logging
import os
import sys
import textwrap
import traceback
from contextlib import redirect_stdout
from typing import List, Optional, Union

import discord
from discord.ext import commands
from discord_slash import SlashCommand
from dotenv import load_dotenv
from pretty_help import Navigation, PrettyHelp

from app import checks
from app.classes.ipc_connection import WebsocketConnection

from ..cache import Cache
from ..database.database import Database

load_dotenv()


class Bot(commands.AutoShardedBot):
    def __init__(self, **kwargs):
        self.stats = {}

        self.theme_color = kwargs.pop("theme_color")
        self.dark_theme_color = kwargs.pop("dark_theme_color")
        self.error_color = kwargs.pop("error_color")
        # self.db: Database = kwargs.pop("db")
        self.db: Database = Database(
            os.getenv("DB_NAME"),
            os.getenv("DB_USER"),
            os.getenv("DB_PASSWORD"),
        )
        self.cache = Cache(self)

        self.pipe = kwargs.pop("pipe")
        self.cluster_name = kwargs.pop("cluster_name")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        help_emojis = Navigation("⬅️", "➡️", "⏹️")

        super().__init__(
            help_command=PrettyHelp(
                color=self.theme_color,
                navigation=help_emojis,
                command_attrs={"name": "commands", "hidden": True},
            ),
            command_prefix=self._prefix_callable,
            **kwargs,
            loop=loop,
        )
        self._last_result = None
        log = logging.getLogger(f"Cluster#{self.cluster_name}")
        log.setLevel(logging.DEBUG)
        log.handlers = [
            logging.FileHandler(
                f"logs/cluster-{self.cluster_name}.log",
                encoding="utf-8",
                mode="a",
            )
        ]

        self.websocket = WebsocketConnection(
            self.cluster_name, self.handle_websocket_command, self.loop
        )
        self.loop.run_until_complete(self.websocket.ensure_connection())

        log.info(
            f'[Cluster#{self.cluster_name}] {kwargs["shard_ids"]}, '
            f'{kwargs["shard_count"]}'
        )
        self.log = log
        # self.loop.create_task(self.ensure_ipc())

        self.loop.run_until_complete(self.db.init_database())

        self.slash = SlashCommand(self, override_type=True)

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
            guild = await self.db.guilds.get(message.guild.id)
            if not guild:
                prefixes = ["sb!"]
            else:
                prefixes = guild["prefixes"]
        else:
            prefixes = ["sb!"]
        return prefixes + [f"<@{self.user.id}> ", f"<@!{self.user.id}> "]

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

    async def handle_websocket_command(
        self, msg: Union[dict, str]
    ) -> Optional[dict]:
        cmd = msg["name"]
        data = msg["data"]

        ret = None

        if cmd == "ping":
            ret = "pong"
        if cmd == "eval":
            content = data["content"]
            ret = str(await self.exec(content))
        if cmd == "set_stats":
            self.stats[msg["author"]] = {
                "guilds": data["guild_count"],
                "members": data["member_count"],
            }

        return ret
