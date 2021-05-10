import asyncio
import io
import logging
import os
import sys
import textwrap
import traceback
import typing
from contextlib import asynccontextmanager, redirect_stdout
from typing import Any, Optional, SupportsIndex, Union

import aiohttp
import discord
from discord.ext import commands
from discord_slash import SlashCommand
from dotenv import load_dotenv
from pretty_help import PrettyHelp

import config
from app import i18n
from app.classes.context import CustomContext
from app.classes.ipc_connection import WebsocketConnection
from app.i18n.i18n import t_
from app.menus import HelpMenu

from ..database.database import Database

if typing.TYPE_CHECKING:
    from app.cogs.cache.cache import Cache

load_dotenv()


class LimitedList:
    def __init__(self, limit: int = None):
        self._values: list[Any] = []
        self.limit = limit

    def append(self, value: Any):
        self._values.append(value)
        if self.limit and self.limit < len(self):
            self._values = self._values[-self.limit :]

    def pop(self, index: int = 0):
        return self._values.pop(index)

    def remove(self, value: Any):
        return self._values.remove(value)

    def __len__(self):
        return self._values.__len__()

    def __iter__(self):
        return self._values.__iter__()

    def __repr__(self):
        return self._values.__repr__()

    def __str__(self):
        return self._values.__str__()

    def __getitem__(self, i_or_s: Union[SupportsIndex, slice]):
        return self._values.__getitem__(i_or_s)


class Bot(commands.AutoShardedBot):
    def __init__(self, **kwargs):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        self.theme_color = kwargs.pop("theme_color")
        self.dark_theme_color = kwargs.pop("dark_theme_color")
        self.error_color = kwargs.pop("error_color")
        self.cluster_name = kwargs.pop("cluster_name")

        self._last_result = None
        self.stats = {}
        self.locale_cache = {}
        self.to_cleanup: dict[int, LimitedList] = {}

        self.cache: "Cache"

        super().__init__(
            help_command=PrettyHelp(
                color=self.theme_color,
                command_attrs={
                    "name": "_commands",
                    "hidden": True,
                    "enabled": False,
                },
                menu=HelpMenu,
                ending_note=t_(
                    "Type s-commands command for more info on a command.\n"
                    "You can also type s-commands category for more info on "
                    "a category.",
                    True,
                ),
            ),
            command_prefix=self._prefix_callable,
            **kwargs,
            loop=loop,
            activity=discord.Activity(
                type=discord.ActivityType.watching, name="@Starboard help"
            ),
        )

        self.log = logging.getLogger(f"Cluster#{self.cluster_name}")
        self.log.setLevel(logging.DEBUG)

        self.db: Database = Database(
            os.getenv("DB_NAME"),
            os.getenv("DB_USER"),
            os.getenv("DB_PASSWORD"),
        )
        self.pipe = kwargs.pop("pipe")
        self.slash = SlashCommand(self, override_type=True, sync_commands=True)
        self.websocket = WebsocketConnection(
            self.cluster_name, self.handle_websocket_command, self.loop
        )

        self.loop.run_until_complete(self.websocket.ensure_connection())
        self.loop.run_until_complete(self.db.init_database())

        self.log.info(
            f'[Cluster#{self.cluster_name}] {kwargs["shard_ids"]}, '
            f'{kwargs["shard_count"]}'
        )

        for ext in kwargs.pop("initial_extensions"):
            self.load_extension(ext)

        self.loop.run_until_complete(self.set_session())

        try:
            self.run(kwargs["token"])
        except Exception as e:
            raise e from e
        else:
            sys.exit(-1)

    async def is_owner(self, user: discord.User):
        if user.id in config.OWNER_IDS:
            return True
        return False

    async def get_context(self, message, *, cls=CustomContext):
        return await super().get_context(message, cls=cls)

    def register_cleanup(self, message: discord.Message):
        if not message.guild:
            return
        if message.guild.id not in self.to_cleanup:
            self.to_cleanup[message.guild.id] = LimitedList(100)
        self.to_cleanup[message.guild.id].append(message.id)

    async def set_session(self):
        self.session = aiohttp.ClientSession()

    def get_webhook(self, url: str) -> discord.Webhook:
        return discord.Webhook.from_url(
            url, adapter=discord.AsyncWebhookAdapter(self.session)
        )

    @asynccontextmanager
    async def temp_locale(
        self, obj: Union[discord.User, discord.Member, discord.Guild]
    ):
        revert_to = i18n.current_locale.get()
        try:
            await self.set_locale(obj)
            yield
        finally:
            i18n.current_locale.set(revert_to)

    async def set_locale(
        self, obj: Union[discord.User, discord.Member, discord.Guild]
    ):
        if obj.id in self.locale_cache:
            locale = self.locale_cache[obj.id]
        else:
            if isinstance(obj, (discord.User, discord.Member)):
                sql_user = await self.db.users.get(obj.id)
                locale = sql_user["locale"] if sql_user else "en_US"
            else:
                sql_guild = await self.db.guilds.get(obj.id)
                locale = sql_guild["locale"] if sql_guild else "en_US"

            self.locale_cache[obj.id] = locale

        i18n.current_locale.set(locale)

    async def on_message(self, message):
        pass

    async def on_error(self, event: str, *args, **kwargs) -> None:
        _, error, _ = sys.exc_info()
        self.dispatch("log_error", "Error", error, args, kwargs)

    async def _prefix_callable(
        self, bot, message: discord.Message, when_mentioned: bool = True
    ) -> list[str]:
        if message.guild:
            guild = await self.db.guilds.get(message.guild.id)
            if not guild:
                prefixes = ["sb!"]
            else:
                prefixes = guild["prefixes"]
        else:
            prefixes = ["sb!"]
        prefixes = list(sorted(prefixes, key=len, reverse=True))
        if when_mentioned:
            return commands.when_mentioned_or(*prefixes)(bot, message)
        return prefixes

    def cleanup_code(self, content):
        """Automatically removes code blocks from the code."""
        # remove ```py\n```
        if content.startswith("```") and content.endswith("```"):
            return "\n".join(content.split("\n")[1:-1])

        # remove `foo`
        return content.strip("` \n")

    async def close(self, *args, **kwargs):
        await self.db.pool.close()
        await self.session.close()
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
        self, msg: dict[str, Any]
    ) -> Optional[Union[list, str, bool, dict[Any, Any]]]:
        cmd = msg["name"]
        data = msg["data"]

        ret: Optional[Union[list, str, dict[Any, Any]]] = None

        if cmd == "ping":
            ret = "pong"
        elif cmd == "eval":
            content = data["content"]
            ret = str(await self.exec(content))
        elif cmd == "set_stats":
            self.stats[msg["author"]] = {
                "guilds": data["guild_count"],
                "members": data["member_count"],
            }
        elif cmd == "get_mutual":
            ret = []
            for gid in data:
                if self.get_guild(gid):
                    ret.append(gid)
        elif cmd == "is_mutual":
            if self.get_guild(data["gid"]):
                ret = True
            else:
                ret = False
        elif cmd == "channel_names":
            ret = {}
            for cid in data["channel_ids"]:
                obj = self.get_channel(cid)
                if obj:
                    ret[cid] = obj.name
        elif cmd == "guild_channels":
            guild = self.get_guild(data["guild_id"])
            ret = {}
            if guild:
                for c in guild.text_channels:
                    key = str(c.category or "No Category")
                    ret.setdefault(key, {})
                    ret[key][c.id] = c.name
        elif cmd == "donate_event":
            self.dispatch("donatebot_event", data["data"], data["auth"])
        elif cmd == "update_prem_roles":
            self.dispatch("update_prem_roles", int(data["user_id"]))

        return ret
