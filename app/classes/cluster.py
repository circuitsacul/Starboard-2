import logging
import multiprocessing
import os
import signal

from discord import AllowedMentions, Intents

import config
from app.cache import Cache
from app.classes.bot import Bot
from app.utils import webhooklog

EXTENSIONS = [
    "app.cogs.base.base_commands",
    "app.cogs.base.base_events",
    "app.cogs.starboard.starboard_commands",
    "app.cogs.starboard.starboard_events",
    "app.cogs.owner.eval",
    "app.cogs.owner.owner_commands",
    "app.cogs.cache.cache_events",
    "app.cogs.settings.settings_commands",
    "app.cogs.utility.utility_commands",
    "app.cogs.fun.fun_commands",
    "app.cogs.quick_actions.qa_events",
    "app.cogs.stats.stats_events",
    "app.cogs.autostarchannels.asc_commands",
    "app.cogs.autostarchannels.asc_events",
    "app.cogs.slash.slash_commands",
    "app.cogs.slash.slash_events",
    "app.cogs.blacklist.bl_commands",
    "jishaku",
]
INTENTS = Intents(
    messages=True, guilds=True, emojis=True, reactions=True, members=True
)
NO_MENTIONS = AllowedMentions.none()
TOKEN = os.getenv("TOKEN")
UPTIME_HOOK = os.getenv("UPTIME_HOOK")


class Cluster:
    def __init__(self, launcher, name, shard_ids, max_shards):
        self.launcher = launcher
        self.process = None
        self.kwargs = dict(
            intents=INTENTS,
            allowed_mentions=NO_MENTIONS,
            case_insensitive=True,
            token=TOKEN,
            shard_ids=shard_ids,
            shard_count=max_shards,
            cluster_name=name,
            cache=Cache(),
            theme_color=config.THEME_COLOR,
            dark_theme_color=config.DARK_THEME_COLOR,
            error_color=config.ERROR_COLOR,
            initial_extensions=EXTENSIONS,
        )
        self.name = name
        self.log = logging.getLogger(f"Cluster#{name}")
        self.log.setLevel(logging.DEBUG)
        hdlr = logging.StreamHandler()
        hdlr.setFormatter(
            logging.Formatter(
                "[%(asctime)s %(name)s/%(levelname)s] %(message)s"
            )
        )
        fhdlr = logging.FileHandler(
            "logs/cluster-Launcher.log", encoding="utf-8"
        )
        fhdlr.setFormatter(
            logging.Formatter(
                "[%(asctime)s %(name)s/%(levelname)s] %(message)s"
            )
        )
        self.log.handlers = [hdlr, fhdlr]
        self.log.info(
            f"Initialized with shard ids {shard_ids}, "
            f"total shards {max_shards}"
        )

    def wait_close(self):
        return self.process.join()

    async def start(self, *, force=False):
        if self.process and self.process.is_alive():
            if not force:
                self.log.warning(
                    "Start called with already running cluster, "
                    "pass `force=True` to override"
                )
                return
            self.log.info("Terminating existing process")
            self.process.terminate()
            self.process.close()

        webhooklog(
            f":yellow_circle: Cluster **{self.name}** logging in...",
            UPTIME_HOOK,
        )

        stdout, stdin = multiprocessing.Pipe()
        kw = self.kwargs
        kw["pipe"] = stdin
        self.process = multiprocessing.Process(
            target=Bot, kwargs=kw, daemon=True
        )
        self.process.start()
        self.log.info(f"Process started with PID {self.process.pid}")

        if await self.launcher.loop.run_in_executor(None, stdout.recv) == 1:
            stdout.close()
            self.log.info("Process started successfully")

        return True

    def stop(self, sign=signal.SIGINT):
        self.log.info(f"Shutting down with signal {sign!r}")
        webhooklog(
            f":brown_circle: Cluster **{self.name}** shutting down...",
            UPTIME_HOOK,
        )
        try:
            self.process.kill()
            os.kill(self.process.pid, sign)
        except ProcessLookupError:
            pass
