from typing import Any

import discord

from ..bot import Bot
from .. import errors
from .starboard import Starboard


class Guild:
    def __init__(self, bot: Bot, **kwargs: dict) -> None:
        self.bot = bot

        self.guild = kwargs.pop('guild')
        self._sql_attributes = kwargs.copy()

        self.id = int(kwargs.pop('id'))

        self.log_channel = int(kwargs.pop('log_channel'))
        self.level_channel = int(kwargs.pop('level_channel'))
        self.ping_user = kwargs.pop('ping_user')

        self.prefixes = kwargs.pop('prefixes')

        self._starboards = None

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
                    self.bot.get_channel(int(s['id'])),
                    **s
                )
                for s in sql_starboards
            ]
        return self._starboards

    @classmethod
    async def from_guild(
        cls: Any,
        bot: Bot,
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

        return cls(bot, guild=guild, **sql_guild)

    @classmethod
    async def from_id(
        cls: Any,
        bot: Bot,
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

        return cls(bot, guild=guild, **sql_guild)
