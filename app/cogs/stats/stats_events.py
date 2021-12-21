from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

import psutil
from discord.ext import tasks

import config
from app import commands

if TYPE_CHECKING:
    from app.classes.bot import Bot
    from app.classes.context import MyContext


class StatsEvents(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self.statcord_key = os.getenv("STATCORD_TOKEN")

        # stats for all clusters
        self.statcord_stats: dict[str, dict[str, Any]] = {}

        # stats for current cluster
        self.popular_commands: dict[str, int] = {}
        self.commands_run: int = 0
        self.active_users: set[int] = set()

        self.broadcast_stats.start()
        if 0 in bot.shard_ids:
            if not config.DEVELOPMENT:
                self.post_botblock.start()
            if config.POST_STATCORD:
                self.post_statcord.start()

    @commands.Cog.listener()
    async def on_command(self, ctx: MyContext):
        if ctx.command_failed:
            return

        self.popular_commands.setdefault(ctx.command.name, 0)
        self.popular_commands[ctx.command.name] += 1
        self.commands_run += 1
        self.active_users.add(ctx.author.id)

    @commands.Cog.listener()
    async def on_stats_updated(self, cluster_name: str, data: dict[str, Any]):
        self.bot.stats[cluster_name] = {
            "guilds": data["guilds"],
            "members": data["members"],
        }

        self.statcord_stats.setdefault(
            cluster_name, dict(popular={}, active=set(), run=0)
        )
        # popular commands
        for cmd, count in data["popular_commands"]:
            self.statcord_stats[cluster_name]["popular"].setdefault(cmd, 0)
            self.statcord_stats[cluster_name]["popular"][cmd] += count
        # active users
        self.statcord_stats[cluster_name]["active"].update(
            data["active_users"]
        )
        # commands run
        self.statcord_stats[cluster_name]["run"] += data["commands_run"]

    @tasks.loop(minutes=1)
    async def post_statcord(self):
        await self.bot.wait_until_ready()

        servers = sum([d["guilds"] for d in self.bot.stats])
        members = sum([d["members"] for d in self.bot.stats])

        commands_run = 0
        active_users = set()
        popular_commands = {}
        for _, stats in self.statcord_stats.items():
            commands_run += stats["run"]
            active_users.update(stats["active"])
            for cmd, count in stats["popular"].items():
                popular_commands.setdefault(cmd, 0)
                popular_commands[cmd] += count

        _mem = psutil.virtual_memory()
        mem_used = str(_mem.used)
        mem_load = str(_mem.percent)
        cpu_load = str(psutil.cpu_percent())
        # TODO: network usage

        # reset stats
        self.statcord_stats = {}

        data = {
            "id": str(self.bot.user.id),
            "key": self.statcord_key,
            "servers": str(servers),
            "users": str(members),
            "commands": str(commands_run),
            "active": list(active_users),
            "popular": [
                {"name": k, "count": v} for k, v in popular_commands.items()
            ],
            "memactive": mem_used,
            "memload": mem_load,
            "cpuload": cpu_load,
            "bandwidth": "0",
        }

        session = await self.bot.session()
        async with session.post(
            "https://api.statcord.com/v3/stats",
            json=data,
            headers={"Content-Type": "application/json"},
        ) as resp:
            resp.raise_for_status()

    @tasks.loop(minutes=30)
    async def post_botblock(self):
        await self.bot.wait_until_ready()
        params = {
            "server_count": sum(
                [s["guilds"] for _, s in self.bot.stats.items()]
            ),
            "bot_id": self.bot.user.id,
            **config.BOT_LISTS,
        }
        session = await self.bot.session()
        async with session.post(
            "https://botblock.org/api/count", data=params
        ) as resp:
            resp.raise_for_status()
            data = await resp.json()
            if len(data["failure"]) != 0:
                for botlist, info in data["failure"].items():
                    print(f"Posting stats to {botlist} failed: {info}")

    @tasks.loop(minutes=1)
    async def broadcast_stats(self) -> None:
        await self.bot.wait_until_ready()
        member_count = sum(
            [
                g.member_count
                for g in self.bot.guilds
                if hasattr(g, "member_count") and g.member_count is not None
            ]
        )

        await self.bot.websocket.send_command(
            "set_stats",
            {
                "guilds": len(self.bot.guilds),
                "members": member_count,
                "popular_commands": self.popular_commands,
                "active_users": list(self.active_users),
                "commands_run": self.commands_run,
            },
        )

        # reset counters
        self.popular_commands = {}
        self.active_users = set()
        self.commands_run = 0


def setup(bot: Bot) -> None:
    bot.add_cog(StatsEvents(bot))
