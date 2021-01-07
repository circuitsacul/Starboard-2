from typing import Any

import discord

from ..bot import Bot
from .. import errors


class Starboard:
    def __init__(self, bot: Bot, **kwargs: dict):
        self.bot = bot

        self.channel = kwargs.pop('channel')
        self._sql_attributes = kwargs.copy()

        self.id = int(kwargs.pop('id'))
        self.guild_id = int(kwargs.pop('guild_id'))

        self.threshold = kwargs.pop('threshold')
        self.lower_threshold = kwargs.pop('lower_threshold')
        self.selfstar = kwargs.pop('selfstar')
        self.unstar = kwargs.pop('unstar')
        self.xp = kwargs.pop('xp')
        self.link_edits = kwargs.pop('link_edits')
        self.link_deletes = kwargs.pop('link_deletes')
        self.star_emojis = kwargs.pop('star_emojis')
        self.display_emoji = kwargs.pop('display_emoji')

        self.star = kwargs.pop('star')
        self.recv_star = kwargs.pop('recv_star')

    @classmethod
    async def from_channel(
        cls: Any,
        bot: Bot,
        channel: discord.TextChannel
    ) -> Any:
        async with bot.database.pool.acquire() as con:
            async with con.transaction():
                sql_starboard = await con.fetchrow(
                    """SELECT * FROM starboards
                    WHERE id=$1""", channel.id
                )

        if sql_starboard is None:
            raise errors.DoesNotExist(
                f"No starboard with id of {channel.id} was found."
            )

        return cls(bot, channel=channel, **sql_starboard)

    @classmethod
    async def from_id(
        cls: Any,
        bot: Bot,
        channel_id: int
    ) -> Any:
        async with bot.database.pool.acquire() as con:
            async with con.transaction():
                sql_starboard = await con.fetchrow(
                    """SELECT * FROM starboards
                    WHERE id=$1""", channel_id
                )

        if sql_starboard is None:
            raise errors.DoesNotExist(
                f"No starboard with id {channel_id} was found."
            )

        channel = bot.get_channel(channel_id)
        # Channel might be NoneType, but we can still continue

        return cls(bot, channel=channel, **sql_starboard)
