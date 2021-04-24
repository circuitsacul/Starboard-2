import os
from typing import Any

from app.database.database import Database


class NotReady(Exception):
    def __init__(self):
        super().__init__("Database not initialized.")


class Wrapper:
    def __init__(self):
        self.db = Database(
            os.getenv("DB_NAME"),
            os.getenv("DB_USER"),
            os.getenv("DB_PASSWORD"),
        )
        self.ready = False

    def raise_if_not_ready(self):
        if not self.ready:
            raise NotReady()

    async def init(self):
        await self.db.init_database()
        self.ready = True

    async def get_starboards(self, guild_id: int) -> list[dict[str, Any]]:
        self.raise_if_not_ready()
        return await self.db.starboards.get_many(guild_id)

    async def get_starboard(self, starboard_id: int) -> dict[str, Any]:
        self.raise_if_not_ready()
        return await self.db.starboards.get(starboard_id)
