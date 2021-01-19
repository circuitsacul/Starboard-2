from typing import Optional

import discord
from discord.ext import commands

from app.classes.bot import Bot
from app import utils
from app.cogs.starboard import starboard_funcs
from app.cogs.utility import utility_funcs
from . import qa_funcs


class QAEvents(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self.qa_map = {
            'qa_force': qa_force,
            'qa_unforce': qa_unforce,
            'qa_trash': qa_trash,
            'qa_save': qa_save
        }

    @commands.Cog.listener()
    async def on_raw_reaction_add(
        self, payload: discord.RawReactionActionEvent
    ) -> None:
        qa_type: Optional[str]
        emoji: str
        message: Optional[discord.Message]
        orig_message: Optional[dict]

        if not payload.guild_id:
            user = await self.bot.fetch_user(payload.user_id)
            if payload.emoji.name == "❌":
                m = await user.fetch_message(
                    payload.message_id
                )
                if m.author.id != self.bot.user.id:
                    return
                await m.delete()
            return
        if payload.member.bot:
            return

        await self.bot.db.create_guild(payload.guild_id)

        sql_guild = await self.bot.db.get_guild(payload.guild_id)
        if not sql_guild['qa_enabled']:
            return
        emoji = utils.clean_emoji(payload.emoji)
        if emoji in await starboard_funcs.sbemojis(
            self.bot, payload.guild_id
        ):
            return
        qa_type = qa_funcs.get_qa_type(emoji, sql_guild)
        if qa_type is None:
            return

        message = await self.bot.cache.fetch_message(
            self.bot, payload.guild_id,
            payload.channel_id, payload.message_id
        )
        if not message:
            return

        orig_message = await starboard_funcs.orig_message(
            self.bot, payload.message_id
        )
        if not orig_message:
            guild = self.bot.get_guild(payload.guild_id)
            channel = guild.get_channel(payload.channel_id)
            await self.bot.db.create_message(
                payload.message_id,
                payload.guild_id,
                payload.channel_id,
                payload.member.id,
                channel.is_nsfw()
            )
            orig_message = await self.bot.db.get_message(
                payload.message_id
            )

        status: bool = True
        if qa_type in self.qa_map:
            status = await self.qa_map[qa_type](
                self.bot, orig_message, payload.member
            )
        if status is True:
            try:
                await message.remove_reaction(payload.emoji, payload.member)
            except (discord.errors.Forbidden, discord.errors.NotFound):
                pass


async def qa_force(
    bot: Bot, orig_message: dict, member: discord.Member
) -> bool:
    if not member.guild_permissions.manage_messages:
        return False
    await utility_funcs.handle_forcing(
        bot, orig_message['id'], orig_message['guild_id'],
        [], True
    )
    return True


async def qa_unforce(
    bot: Bot, orig_message: dict, member: discord.Member
) -> bool:
    if not member.guild_permissions.manage_messages:
        return False
    await utility_funcs.handle_forcing(
        bot, orig_message['id'], orig_message['guild_id'],
        [], False
    )
    return True


async def qa_trash(
    bot: Bot, orig_message: dict, member: discord.Member
) -> bool:
    if not member.guild_permissions.manage_messages:
        return False
    await utility_funcs.handle_trashing(
        bot, orig_message['id'], orig_message['guild_id'],
        not orig_message['trashed']
    )
    return True


async def qa_save(
    bot: Bot, orig_message: dict, member: discord.Member
) -> bool:
    if orig_message['trashed']\
            and not member.guild_permissions.manage_messages:
        try:
            await member.send("You cannot save a trashed message.")
        except discord.Forbidden:
            pass
        return
    message = await bot.cache.fetch_message(
        bot, orig_message['guild_id'], orig_message['channel_id'],
        orig_message['id']
    )
    if not message:
        return
    embed, attachments = await starboard_funcs.embed_message(
        bot, message
    )
    try:
        await member.send(embed=embed, files=attachments)
    except discord.Forbidden:
        pass
    return True


def setup(bot: Bot) -> None:
    bot.add_cog(QAEvents(bot))
