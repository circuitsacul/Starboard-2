import pathlib
import time
from typing import Any, Dict, List, Optional

import asyncpg

from .database_functions import (
    aschannels,
    autoredeem,
    guilds,
    members,
    messages,
    permgroups,
    permroles,
    posroles,
    reactions,
    sb_messags,
    starboards,
    users,
    xproles,
)


class Database:
    def __init__(self, database: str, user: str, password: str) -> None:
        self.name = database
        self.user = user
        self.password = password

        self.pool: Optional[asyncpg.pool.Pool] = None

        self.sql_times: dict = {}

        self.guilds = guilds.Guilds(self)
        self.members = members.Members(self)
        self.users = users.Users(self)
        self.autoredeem = autoredeem.Autoredeem(self)
        self.aschannels = aschannels.ASChannels(self)
        self.starboards = starboards.Starboards(self)
        self.permgroups = permgroups.PermGroups(self)
        self.permroles = permroles.PermRoles(self)
        self.xproles = xproles.XPRoles(self)
        self.posroles = posroles.PosRoles(self)
        self.messages = messages.Messages(self)
        self.sb_messages = sb_messags.SBMessages(self)
        self.reactions = reactions.Reactions(self)

    def log(self, sql: str, time: float) -> None:
        self.sql_times.setdefault(sql, [])
        self.sql_times[sql].append(time)

    async def init_database(self) -> None:
        self.pool = await asyncpg.create_pool(
            database=self.name,
            user=self.user,
            password=self.password,
            host="127.0.0.1",
        )
        app_dir = pathlib.Path("app/database/")

        async with self.pool.acquire() as con:
            async with con.transaction():
                with open(app_dir / "types.sql", "r") as f:
                    await con.execute(f.read())
                with open(app_dir / "tables.sql", "r") as f:
                    await con.execute(f.read())
                with open(app_dir / "indexes.sql", "r") as f:
                    await con.execute(f.read())

    async def execute(self, sql: str, *args: Any) -> None:
        async with self.pool.acquire() as con:
            async with con.transaction():
                s = time.perf_counter()
                await con.execute(sql, *args)
        self.log(sql, time.perf_counter() - s)

    async def fetch(self, sql: str, *args: Any) -> List[Dict]:
        async with self.pool.acquire() as con:
            async with con.transaction():
                s = time.perf_counter()
                result = await con.fetch(sql, *args)
        self.log(sql, time.perf_counter() - s)
        return result

    async def fetchrow(self, sql: str, *args: Any) -> Optional[dict]:
        async with self.pool.acquire() as con:
            async with con.transaction():
                s = time.perf_counter()
                result = await con.fetchrow(sql, *args)
        self.log(sql, time.perf_counter() - s)
        return result

    async def fetchval(self, sql: str, *args: Any) -> Optional[Any]:
        async with self.pool.acquire() as con:
            async with con.transaction():
                s = time.perf_counter()
                result = await con.fetchval(sql, *args)
        self.log(sql, time.perf_counter() - s)
        return result
