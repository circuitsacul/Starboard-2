from typing import Any

import discord

from .. import errors


class Message:
    def __init__(self, bot, **kwargs: dict) -> None:
        self.bot = bot

        self.message = kwargs.pop("message")
        self._sql_attributes = kwargs.copy()

        self.id = kwargs.get("id")
        self.guild_id = kwargs.get("guild_id")
        self.channel_id = kwargs.get("channel_id")
        self.author_id = kwargs.get("author_id")

        self.points = kwargs.get("points")

        self.forced = kwargs.get("forced")
        self.trashed = kwargs.get("trashed")

    async def delete(self) -> None:
        async with self.bot.database.pool.acquire() as con:
            async with con.transaction():
                await con.execute(
                    """DELETE FROM messages
                    WHERE id=$1""", self.id
                )

    @classmethod
    async def create(
        cls: Any,
        bot,
        message: discord.Message
    ) -> Any:
        async with bot.database.pool.acquire() as con:
            async with con.transaction():
                await con.execute(
                    """INSERT INTO messages
                    (id, guild_id, channel_id, author_id)
                    VALUES ($1, $2, $3, $4)""",
                    message.id, message.guild.id,
                    message.channel.id, message.author.id
                )

        return await cls.from_message(bot, message)

    @classmethod
    async def from_message(
        cls: Any,
        bot,
        message: discord.Message
    ) -> Any:
        async with bot.database.pool.acquire() as con:
            async with con.transaction():
                sql_message = await con.fetchrow(
                    """SELECT * FROM messages
                    WHERE id=$1""", message.id
                )

        if sql_message is None:
            raise errors.DoesNotExist(
                f"No message with id {message.id}"
            )

        return cls(bot, message=message, **sql_message)

    @classmethod
    async def from_id(
        cls: Any,
        bot,
        message_id: int
    ) -> Any:
        async with bot.database.pool.acquire() as con:
            async with con.transaction():
                sql_message = await con.fetchrow(
                    """SELECT * FROM messages
                    WHERE id=$1""", message_id
                )

        if sql_message is None:
            raise errors.DoesNotExist(
                f"No message with id {message_id}"
            )

        channel = bot.get_channel(int(sql_message['channel_id']))
        message = await channel.fetch_message(int(sql_message['id']))

        return cls(bot, message=message, **sql_message)
