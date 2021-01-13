import discord
from discord.ext import commands

from app.classes.bot import Bot
from app import utils


class StarboardEvents(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_raw_reaction_add(
        self,
        payload: discord.RawReactionActionEvent
    ) -> None:
        if payload.member.bot:
            return

        emoji = utils.clean_emoji(payload.emoji)

        starboards = await self.bot.db.get_starboards(payload.guild_id)
        sb_emojis = []
        for s in starboards:
            sb_emojis += s['star_emojis']

        if emoji not in sb_emojis:
            return

        message = await self.bot.cache.fetch_message(
            self.bot, payload.guild_id, payload.channel_id,
            payload.message_id
        )

        await self.bot.db.create_member(
            payload.member.id, payload.guild_id
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

    @commands.Cog.listener()
    async def on_raw_reaction_remove(
        self,
        payload: discord.RawReactionActionEvent
    ) -> None:
        emoji = utils.clean_emoji(payload.emoji)

        await self.bot.db.delete_reaction_user(
            emoji, payload.message_id, payload.user_id
        )


def setup(bot: Bot) -> None:
    bot.add_cog(StarboardEvents(bot))
