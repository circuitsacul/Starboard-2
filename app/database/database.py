import asyncpg

from .pg_tables import ALL_TABLES


class Database:
    def __init__(
        self,
        database: str,
        user: str,
        password: str
    ) -> None:
        self.name = database
        self.user = user
        self.password = password

        self.pool: asyncpg.pool.Pool = None

    async def init_database(
        self
    ) -> None:
        self.pool = await asyncpg.create_pool(
            database=self.name,
            user=self.user,
            password=self.password
        )

        async with self.pool.acquire() as con:
            async with con.transaction():
                for table in ALL_TABLES:
                    await con.execute(table)
