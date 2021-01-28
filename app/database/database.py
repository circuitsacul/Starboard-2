import time
from typing import Any, List, Optional

import asyncpg

from .database_functions import (
    aschannels,
    guilds,
    members,
    messages,
    reactions,
    sb_messags,
    starboards,
    users,
)
from .pg_indexes import ALL_INDEXES
from .pg_tables import ALL_TABLES


class Database:
    def __init__(self, bot, database: str, user: str, password: str) -> None:
        self.bot = bot

        self.name = database
        self.user = user
        self.password = password

        self.pool: asyncpg.pool.Pool = None

        self.sql_times: dict = {}

        self.guilds = guilds.Guilds(bot)
        self.members = members.Members(bot)
        self.users = users.Users(bot)
        self.aschannels = aschannels.ASChannels(bot)
        self.starboards = starboards.Starboards(bot)
        self.messages = messages.Messages(bot)
        self.sb_messages = sb_messags.SBMessages(bot)
        self.reactions = reactions.Reactions(bot)

    def log(self, sql: str, time: float) -> None:
        self.sql_times.setdefault(sql, [])
        self.sql_times[sql].append(time)

    async def init_database(self) -> None:
        self.pool = await asyncpg.create_pool(
            database=self.name, user=self.user, password=self.password
        )

        async with self.pool.acquire() as con:
            async with con.transaction():
                for table in ALL_TABLES:
                    await con.execute(table)
                for index in ALL_INDEXES:
                    await con.execute(index)

    async def execute(self, sql: str, *args: list) -> None:
        async with self.pool.acquire() as con:
            async with con.transaction():
                s = time.time()
                await con.execute(sql, *args)
        self.log(sql, time.time() - s)

    async def fetch(self, sql: str, *args: list) -> List[dict]:
        async with self.pool.acquire() as con:
            async with con.transaction():
                s = time.time()
                result = await con.fetch(sql, *args)
        self.log(sql, time.time() - s)
        return result

    async def fetchrow(self, sql: str, *args: list) -> Optional[dict]:
        async with self.pool.acquire() as con:
            async with con.transaction():
                s = time.time()
                result = await con.fetchrow(sql, *args)
        self.log(sql, time.time() - s)
        return result

    async def fetchval(self, sql: str, *args: list) -> Optional[Any]:
        async with self.pool.acquire() as con:
            async with con.transaction():
                s = time.time()
                result = await con.fetchval(sql, *args)
        self.log(sql, time.time() - s)
        return result
