import discord
from discord.ext import commands

from app import utils
from app.classes.bot import Bot
from app.cogs.utility import utility_funcs

from . import starboard_funcs


class StarboardEvents(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_guild_channel_delete(
        self, channel: discord.abc.GuildChannel
    ) -> None:
        if not isinstance(channel, discord.TextChannel):
            return
        starboard = await self.bot.db.get_starboard(channel.id)
        if not starboard:
            return
        await self.bot.db.execute(
            """DELETE FROM starboards WHERE id=$1""", channel.id
        )
        self.bot.dispatch(
            "guild_log",
            (f"`{channel.name}` was deleted, so I removed " "that starboard."),
            "info",
            channel.guild,
        )

    @commands.Cog.listener()
    async def on_raw_message_delete(
        self, payload: discord.RawMessageDeleteEvent
    ) -> None:
        sb_message = await self.bot.db.get_starboard_message(
            payload.message_id
        )
        if sb_message:
            # Trash the message
            await utility_funcs.handle_trashing(
                self.bot,
                sb_message["orig_id"],
                payload.guild_id,
                True,
                reason=("Starboard message was deleted, so I autotrashed it."),
            )

    @commands.Cog.listener()
    async def on_raw_reaction_add(
        self, payload: discord.RawReactionActionEvent
    ) -> None:
        # Check if bot
        if not payload.guild_id:
            return
        if payload.member.bot:
            return

        # Check if is starEmoji
        emoji = utils.clean_emoji(payload.emoji)
        starboards = await self.bot.db.get_starboards(payload.guild_id)
        sb_emojis = []
        for s in starboards:
            sb_emojis += s["star_emojis"]

        if emoji not in sb_emojis:
            return

        # Create necessary data
        await self.bot.db.create_user(payload.member.id, payload.member.bot)
        await self.bot.db.create_member(payload.member.id, payload.guild_id)

        # Add reaction
        sql_message = await starboard_funcs.orig_message(
            self.bot, payload.message_id
        )
        if sql_message is not None:
            # Get the message since it already exists
            message = await self.bot.cache.fetch_message(
                self.bot,
                int(sql_message["guild_id"]),
                int(sql_message["channel_id"]),
                int(sql_message["id"]),
            )
            await self.bot.db.create_reaction_user(
                emoji, sql_message["id"], payload.user_id
            )
            await starboard_funcs.update_message(
                self.bot, sql_message["id"], sql_message["guild_id"]
            )
        else:
            # Get the message as well as add it to the database
            message = await self.bot.cache.fetch_message(
                self.bot,
                payload.guild_id,
                payload.channel_id,
                payload.message_id,
            )

            await self.bot.db.create_user(
                message.author.id, message.author.bot
            )
            await self.bot.db.create_member(
                message.author.id, payload.guild_id
            )
            await self.bot.db.create_message(
                message.id,
                message.guild.id,
                message.channel.id,
                message.author.id,
                message.channel.is_nsfw(),
            )
            await self.bot.db.create_reaction_user(
                emoji, message.id, payload.user_id
            )
            await starboard_funcs.update_message(
                self.bot, payload.message_id, payload.guild_id
            )

    @commands.Cog.listener()
    async def on_raw_reaction_remove(
        self, payload: discord.RawReactionActionEvent
    ) -> None:
        if not payload.guild_id:
            return
        emoji = utils.clean_emoji(payload.emoji)

        sb_emojis = []
        starboards = await self.bot.db.get_starboards(payload.guild_id)
        for s in starboards:
            sb_emojis += s["star_emojis"]
        if emoji not in sb_emojis:
            return

        orig_message = await starboard_funcs.orig_message(
            self.bot, payload.message_id
        )

        if orig_message is not None:
            # Delete from the original message
            await self.bot.db.delete_reaction_user(
                emoji, int(orig_message["id"]), payload.user_id
            )

            await starboard_funcs.update_message(
                self.bot, orig_message["id"], payload.guild_id
            )
        else:
            # Delete from the message since it is the original
            await self.bot.db.delete_reaction_user(
                emoji, payload.message_id, payload.user_id
            )

            await starboard_funcs.update_message(
                self.bot, payload.message_id, payload.guild_id
            )


def setup(bot: Bot) -> None:
    bot.add_cog(StarboardEvents(bot))
