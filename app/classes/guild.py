from typing import Any

import discord

from .. import errors
from .starboard import Starboard


class Guild:
    def __init__(self, bot, **kwargs: dict) -> None:
        self.bot = bot

        self.guild = kwargs.pop('guild')
        self._sql_attributes = kwargs.copy()

        self.id = kwargs.get('id')

        self.log_channel = kwargs.get('log_channel')
        self.level_channel = kwargs.get('level_channel')
        self.ping_user = kwargs.get('ping_user')

        self.prefixes = kwargs.get('prefixes')

        self._starboards = None

    async def get_starboard(self, starboard_id: int) -> Starboard:
        return discord.utils.get(await self.starboards, id=starboard_id)

    async def add_starboard(self, channel_id: int) -> Starboard:
        exists = await self.get_starboard(channel_id) is not None
        if exists:
            raise errors.AlreadyExists(
                f"<#{channel_id}> is already a starboard."
            )
        starboard = await Starboard.create(self.bot, channel_id, self.id)
        self._starboards.append(starboard)
        return starboard

    async def remove_starboard(self, channel_id: int) -> None:
        starboard = await self.get_starboard(channel_id)
        if starboard is None:
            raise errors.DoesNotExist(
                f"<#{channel_id}> is not a starboard."
            )
        await starboard.delete()
        self._starboards.remove(starboard)

    @property
    async def starboards(self) -> list:
        if self._starboards is None:
            async with self.bot.database.pool.acquire() as con:
                async with con.transaction():
                    sql_starboards = await con.fetch(
                        """SELECT * FROM starboards
                        WHERE guild_id=$1""", self.id
                    )
            self._starboards = [
                Starboard(
                    self.bot,
                    channel=self.bot.get_channel(int(s['id'])),
                    **s
                )
                for s in sql_starboards
            ]
        return self._starboards

    @classmethod
    async def from_guild(
        cls: Any,
        bot,
        guild: discord.Guild
    ) -> Any:
        async with bot.database.pool.acquire() as con:
            async with con.transaction():
                sql_guild = await con.fetchrow(
                    """SELECT * FROM guilds
                    WHERE id=$1""", guild.id
                )

        if sql_guild is None:
            raise errors.DoesNotExist(
                f"No guild with id {guild.id}"
            )

        result = cls(bot, guild=guild, **sql_guild)
        bot.cache.guilds.add(result)
        return result

    @classmethod
    async def from_id(
        cls: Any,
        bot,
        guild_id: int
    ) -> Any:
        async with bot.database.pool.acquire() as con:
            async with con.transaction():
                sql_guild = await con.fetchrow(
                    """SELECT * FROm guilds
                    WHERE id=$1""", guild_id
                )

        if sql_guild is None:
            raise errors.DoesNotExist(
                f"No guild with id {guild_id}"
            )

        guild = bot.get_guild(guild_id)

        result = cls(bot, guild=guild, **sql_guild)
        bot.cache.guilds.add(result)
        return result
