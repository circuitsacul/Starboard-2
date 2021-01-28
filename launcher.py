import asyncio
import logging
import multiprocessing
import os
import sys
import time

import requests
from dotenv import load_dotenv

import config
import ipc
from app.classes.cluster import Cluster
from app.utils import webhooklog

load_dotenv()

WEBHOOK_URL = os.getenv("UPTIME_HOOK")
TOKEN = os.getenv("TOKEN")
SHARDS = config.SHARDS

log = logging.getLogger("Cluster#Launcher")
log.setLevel(logging.DEBUG)
hdlr = logging.StreamHandler()
hdlr.setFormatter(
    logging.Formatter("[%(asctime)s %(name)s/%(levelname)s] %(message)s")
)
fhdlr = logging.FileHandler("logs/cluster-Launcher.log", encoding="utf-8")
fhdlr.setFormatter(
    logging.Formatter("[%(asctime)s %(name)s/%(levelname)s] %(message)s")
)
log.handlers = [hdlr, fhdlr]


CLUSTER_NAMES = (
    "Alpha (0)",
    "Beta (1)",
    "Gamma (2)",
    "Delta (3)",
    "Epsilon (4)",
    "Zeta (5)",
    "Eta (6)",
    "Theta (7)",
    "Iota (8)",
    "Kappa (9)",
    "Lambda (10)",
    "Mu (11)",
    "Nu (12)",
    "Xi (13)",
    "Omicron (14)",
    "Pi (15)",
    "Rho (16)",
    "Sigma (17)",
    "Tau (18)",
    "Upsilon (19)",
    "Phi (20)",
    "Chi (21)",
    "Psi (22)",
    "Omega (23)",
)
NAMES = iter(CLUSTER_NAMES)


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
            "https://discordapp.com/api/v7/gateway/bot",
            headers={
                "Authorization": "Bot " + TOKEN,
                "User-Agent": (
                    "DiscordBot (https://github.com/Rapptz/discord.py "
                    "1.3.0a) Python/3.7 aiohttp/3.6.1"
                ),
            },
        )
        data.raise_for_status()
        content = data.json()
        log.info(
            f"Successfully got shard count of {content['shards']}"
            f" ({data.status_code, data.reason})"
        )
        return content["shards"]

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
        if sys.platform == "win32":
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
        size = [shards[x : x + 4] for x in range(0, len(shards), 4)]
        log.info(f"Preparing {len(size)} clusters")
        for shard_ids in size:
            self.cluster_queue.append(
                Cluster(self, next(NAMES), shard_ids, len(shards))
            )

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
                        f":red_circle: Cluster **{cluster.name}** "
                        "is offline.",
                        WEBHOOK_URL,
                    )
                    # if cluster.process.exitcode != 0:
                    #    # ignore safe exits
                    log.info(
                        f"Cluster#{cluster.name} exited with code "
                        f"{cluster.process.exitcode}"
                    )
                    log.info(f"Restarting cluster#{cluster.name}")
                    await cluster.start()
                    # else:
                    #    log.info(f"Cluster#{cluster.name} found dead")
                    #    to_remove.append(cluster)
                    #    cluster.stop()  # ensure stopped
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


if __name__ == "__main__":
    p = multiprocessing.Process(target=ipc.run, daemon=True)
    p.start()
    loop = asyncio.get_event_loop()
    webhooklog(":white_circle: Bot logging in...", WEBHOOK_URL)
    Launcher(loop).start()
    p.kill()
    webhooklog(":brown_circle: Bot logged out.", WEBHOOK_URL)
