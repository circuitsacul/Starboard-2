import discord
from discord.ext import commands

from app.classes.bot import Bot
from app import utils
from . import starboard_funcs


class StarboardEvents(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_raw_reaction_add(
        self,
        payload: discord.RawReactionActionEvent
    ) -> None:
        # Check if bot
        if payload.member.bot:
            return

        # Check if is starEmoji
        emoji = utils.clean_emoji(payload.emoji)
        starboards = await self.bot.db.get_starboards(payload.guild_id)
        sb_emojis = []
        for s in starboards:
            sb_emojis += s['star_emojis']

        if emoji not in sb_emojis:
            return

        # Create necessary data
        await self.bot.db.create_member(
            payload.member.id, payload.guild_id
        )

        # Add reaction
        sql_message = await starboard_funcs.orig_message(
            self.bot, payload.message_id
        )
        if sql_message is not None:
            # Get the message since it already exists
            message = await self.bot.cache.fetch_message(
                self.bot, int(sql_message['guild_id']),
                int(sql_message['channel_id']),
                int(sql_message['id'])
            )
            await self.bot.db.create_reaction_user(
                emoji, sql_message['id'], payload.user_id
            )
            await starboard_funcs.update_message(
                self.bot, sql_message['id'],
                sql_message['guild_id']
            )
        else:
            # Get the message as well as add it to the database
            message = await self.bot.cache.fetch_message(
                self.bot, payload.guild_id,
                payload.channel_id,
                payload.message_id
            )

            await self.bot.db.create_member(
                message.author.id, payload.guild_id
            )
            await self.bot.db.create_message(
                message.id, message.guild.id,
                message.channel.id, message.author.id,
                message.channel.is_nsfw()
            )
            await self.bot.db.create_reaction_user(
                emoji, message.id, payload.user_id
            )
            await starboard_funcs.update_message(
                self.bot, payload.message_id,
                payload.guild_id
            )

    @commands.Cog.listener()
    async def on_raw_reaction_remove(
        self,
        payload: discord.RawReactionActionEvent
    ) -> None:
        emoji = utils.clean_emoji(payload.emoji)

        orig_message = await starboard_funcs.orig_message(
            self.bot, payload.message_id
        )

        if orig_message is not None:
            # Delete from the original message
            await self.bot.db.delete_reaction_user(
                emoji, int(orig_message['id']), payload.user_id
            )

            await starboard_funcs.update_message(
                self.bot, orig_message['id'],
                payload.guild_id
            )
        else:
            # Delete from the message since it is the original
            await self.bot.db.delete_reaction_user(
                emoji, payload.message_id, payload.user_id
            )

            await starboard_funcs.update_message(
                self.bot, payload.message_id,
                payload.guild_id
            )


def setup(bot: Bot) -> None:
    bot.add_cog(StarboardEvents(bot))
