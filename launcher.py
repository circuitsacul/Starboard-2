import asyncio
import logging
import multiprocessing
import signal
import os
import sys
import time
import ipc
from dotenv import load_dotenv

from discord import Webhook, RequestsWebhookAdapter
import requests

from app.classes.bot import Bot
from app.database.database import Database
from app.cache import Cache

load_dotenv()

WEBHOOK_URL = os.getenv("UPTIME_WEBHOOK")
TOKEN = os.getenv('TOKEN')
EXTENSIONS = [
    'app.cogs.base.base_commands',
    'app.cogs.base.base_events',
    'app.cogs.starboard.starboard_commands',
    'app.cogs.owner.eval',
    'app.cogs.owner.owner_commands',
    'jishaku'
]
SHARDS = int(os.getenv("SHARDS"))

log = logging.getLogger("Cluster#Launcher")
log.setLevel(logging.DEBUG)
hdlr = logging.StreamHandler()
hdlr.setFormatter(logging.Formatter(
    "[%(asctime)s %(name)s/%(levelname)s] %(message)s"))
fhdlr = logging.FileHandler("logs/cluster-Launcher.log", encoding='utf-8')
fhdlr.setFormatter(logging.Formatter(
    "[%(asctime)s %(name)s/%(levelname)s] %(message)s"))
log.handlers = [hdlr, fhdlr]


CLUSTER_NAMES = (
    'Alpha (1)', 'Beta (2)', 'Gamma (3)', 'Delta (4)',
    'Epsilon (5)', 'Zeta (6)', 'Eta (7)', 'Theta (8)',
    'Iota (9)', 'Kappa_10', 'Lambda (11)', 'Mu (12)',
    'Nu (13)', 'Xi (14)', 'Omicron (15)', 'Pi (16)',
    'Rho (17)', 'Sigma (18)', 'Tau (19)', 'Upsilon (20)',
    'Phi (21)', 'Chi (22)', 'Psi (23)', 'Omega (24)'
)
NAMES = iter(CLUSTER_NAMES)


def webhooklog(content: str) -> None:
    webhook = Webhook.from_url(
        WEBHOOK_URL, adapter=RequestsWebhookAdapter()
    )
    webhook.send(content, username="Starboard Logs")


class Launcher:
    def __init__(self, loop):
        log.info("Hello, world!")
        self.cluster_queue = []
        self.clusters = []

        self.fut = None
        self.loop = loop
        self.alive = True

        self.keep_alive = None
        self.init = time.perf_counter()

    def get_shard_count(self):
        if SHARDS != 0:
            log.info(f"Launching with {SHARDS} shards")
            return SHARDS
        data = requests.get(
            'https://discordapp.com/api/v7/gateway/bot', headers={
                "Authorization": "Bot "+TOKEN,
                "User-Agent": (
                    "DiscordBot (https://github.com/Rapptz/discord.py "
                    "1.3.0a) Python/3.7 aiohttp/3.6.1"
                )
            }
        )
        data.raise_for_status()
        content = data.json()
        log.info(
            f"Successfully got shard count of {content['shards']}"
            f" ({data.status_code, data.reason})"
        )
        return content['shards']

    def start(self):
        self.fut = asyncio.ensure_future(self.startup(), loop=self.loop)

        try:
            self.loop.run_forever()
        except KeyboardInterrupt:
            self.loop.run_until_complete(self.shutdown())
        finally:
            self.cleanup()

    def cleanup(self):
        self.loop.stop()
        if sys.platform == 'win32':
            print("press ^C again")
        self.loop.close()

    def task_complete(self, task: asyncio.Task):
        if task.cancelled():
            return
        if task.exception():
            task.print_stack()
            self.keep_alive = self.loop.create_task(self.rebooter())
            self.keep_alive.add_done_callback(self.task_complete)

    async def startup(self):
        shards = list(range(self.get_shard_count()))
        size = [shards[x:x + 4] for x in range(0, len(shards), 4)]
        log.info(f"Preparing {len(size)} clusters")
        for shard_ids in size:
            self.cluster_queue.append(
                Cluster(self, next(NAMES), shard_ids, len(shards)))

        await self.start_cluster()
        self.keep_alive = self.loop.create_task(self.rebooter())
        self.keep_alive.add_done_callback(self.task_complete)
        log.info(f"Startup completed in {time.perf_counter()-self.init}s")

    async def shutdown(self):
        log.info("Shutting down clusters")
        self.alive = False
        if self.keep_alive:
            self.keep_alive.cancel()
        for cluster in self.clusters:
            cluster.stop()

    async def rebooter(self):
        while self.alive:
            # log.info("Cycle!")
            if not self.clusters:
                log.warning("All clusters appear to be dead")
                asyncio.ensure_future(self.shutdown())
            to_remove = []
            for cluster in self.clusters:
                if not cluster.process.is_alive():
                    webhooklog(
                        f":black_circle: Cluster **{cluster.name}** "
                        "is offline."
                    )
                    if cluster.process.exitcode != 0:
                        # ignore safe exits
                        log.info(
                            f"Cluster#{cluster.name} exited with code "
                            f"{cluster.process.exitcode}")
                        log.info(f"Restarting cluster#{cluster.name}")
                        await cluster.start()
                    else:
                        log.info(f"Cluster#{cluster.name} found dead")
                        to_remove.append(cluster)
                        cluster.stop()  # ensure stopped
            for rem in to_remove:
                self.clusters.remove(rem)
            await asyncio.sleep(5)

    async def start_cluster(self):
        if self.cluster_queue:
            cluster = self.cluster_queue.pop(0)
            log.info(f"Starting Cluster#{cluster.name}")
            await cluster.start()
            log.info("Done!")
            self.clusters.append(cluster)
            await self.start_cluster()
        else:
            log.info("All clusters launched")


class Cluster:
    def __init__(self, launcher, name, shard_ids, max_shards):
        self.launcher = launcher
        self.process = None
        self.kwargs = dict(
            token=TOKEN,
            command_prefix="sb!",
            shard_ids=shard_ids,
            shard_count=max_shards,
            cluster_name=name,
            cache=Cache(),
            db=Database(
                os.getenv('DB_NAME'),
                os.getenv('DB_USER'),
                os.getenv('DB_PASSWORD')
            ),
            theme_color=os.getenv("THEME"),
            error_color=os.getenv("ERROR"),
            initial_extensions=EXTENSIONS
        )
        self.name = name
        self.log = logging.getLogger(f"Cluster#{name}")
        self.log.setLevel(logging.DEBUG)
        hdlr = logging.StreamHandler()
        hdlr.setFormatter(logging.Formatter(
            "[%(asctime)s %(name)s/%(levelname)s] %(message)s"))
        fhdlr = logging.FileHandler(
            "logs/cluster-Launcher.log", encoding='utf-8')
        fhdlr.setFormatter(logging.Formatter(
            "[%(asctime)s %(name)s/%(levelname)s] %(message)s"))
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
            f":yellow_circle: Cluster **{self.name}** logging in..."
        )

        stdout, stdin = multiprocessing.Pipe()
        kw = self.kwargs
        kw['pipe'] = stdin
        self.process = multiprocessing.Process(
            target=Bot, kwargs=kw, daemon=True
        )
        self.process.start()
        self.log.info(f"Process started with PID {self.process.pid}")

        if await self.launcher.loop.run_in_executor(None, stdout.recv) == 1:
            stdout.close()
            self.log.info("Process started successfully")
            webhooklog(f":green_circle: Cluster **{self.name}** ready!")

        return True

    def stop(self, sign=signal.SIGINT):
        self.log.info(f"Shutting down with signal {sign!r}")
        webhooklog(
            f":red_circle: Cluster **{self.name}** shutting down..."
        )
        try:
            self.process.kill()
            os.kill(self.process.pid, sign)
        except ProcessLookupError:
            pass


if __name__ == "__main__":
    p = multiprocessing.Process(
        target=ipc.run, daemon=True
    )
    p.start()
    loop = asyncio.get_event_loop()
    webhooklog(":white_circle: Bot logging in...")
    Launcher(loop).start()
    p.kill()
    webhooklog(":black_circle: Bot logged out.")
