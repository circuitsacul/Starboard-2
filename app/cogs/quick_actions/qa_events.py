from typing import Optional

import discord

from app import commands, utils
from app.classes.bot import Bot
from app.cogs.starboard import starboard_funcs
from app.cogs.utility import recounter, utility_funcs
from app.i18n import t_

from . import qa_funcs


class QAEvents(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self.qa_map = {
            "qa_force": qa_force,
            "qa_unforce": qa_unforce,
            "qa_trash": qa_trash,
            "qa_save": qa_save,
            "qa_freeze": qa_freeze,
            "qa_recount": qa_recount,
        }

    @commands.Cog.listener()
    async def on_raw_reaction_add(
        self, payload: discord.RawReactionActionEvent
    ) -> None:
        qa_type: Optional[str]
        emoji: str
        message: Optional[discord.Message]
        orig_message: Optional[dict]

        guild = self.bot.get_guild(payload.guild_id)
        if guild:
            await self.bot.set_locale(guild)

        if not payload.guild_id:
            user = await self.bot.fetch_user(payload.user_id)
            if payload.emoji.name == "❌":
                m = await user.fetch_message(payload.message_id)
                if m.author.id != self.bot.user.id:
                    return
                await m.delete()
            return
        if payload.member.bot:
            return

        await self.bot.db.guilds.create(payload.guild_id)

        sql_guild = await self.bot.db.guilds.get(payload.guild_id)
        if not sql_guild["qa_enabled"]:
            return

        emoji = utils.clean_emoji(payload.emoji)
        all_emojis = await starboard_funcs.sbemojis(self.bot, payload.guild_id)
        if emoji in all_emojis:
            return

        qa_type = qa_funcs.get_qa_type(emoji, sql_guild)
        if qa_type is None:
            return

        message = await self.bot.cache.fetch_message(
            payload.guild_id, payload.channel_id, payload.message_id
        )
        if not message:
            return

        orig_message = await starboard_funcs.orig_message(
            self.bot, payload.message_id
        )
        if not orig_message:
            await self.bot.db.messages.create(
                message.id,
                message.guild.id,
                message.channel.id,
                message.author.id,
                message.channel.is_nsfw(),
            )
            orig_message = await self.bot.db.messages.get(payload.message_id)

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


async def qa_recount(
    bot: Bot, orig_message: dict, member: discord.Member
) -> bool:
    if not member.guild_permissions.manage_messages:
        return False
    message = await bot.cache.fetch_message(
        int(orig_message["guild_id"]),
        int(orig_message["channel_id"]),
        int(orig_message["id"]),
    )
    if not message:
        return
    await recounter.recount_reactions(bot, message)
    return True


async def qa_freeze(
    bot: Bot, orig_message: dict, member: discord.Member
) -> bool:
    if not member.guild_permissions.manage_messages:
        return False
    await utility_funcs.handle_freezing(
        bot,
        orig_message["id"],
        orig_message["guild_id"],
        not orig_message["frozen"],
    )
    return True


async def qa_force(
    bot: Bot, orig_message: dict, member: discord.Member
) -> bool:
    if not member.guild_permissions.manage_messages:
        return False
    await utility_funcs.handle_forcing(
        bot, orig_message["id"], orig_message["guild_id"], [], True
    )
    return True


async def qa_unforce(
    bot: Bot, orig_message: dict, member: discord.Member
) -> bool:
    if not member.guild_permissions.manage_messages:
        return False
    await utility_funcs.handle_forcing(
        bot, orig_message["id"], orig_message["guild_id"], [], False
    )
    return True


async def qa_trash(
    bot: Bot, orig_message: dict, member: discord.Member
) -> bool:
    if not member.guild_permissions.manage_messages:
        return False
    await utility_funcs.handle_trashing(
        bot,
        orig_message["id"],
        orig_message["guild_id"],
        not orig_message["trashed"],
        "Used QuickActions to trash",
    )
    return True


async def qa_save(
    bot: Bot, orig_message: dict, member: discord.Member
) -> bool:
    if (
        orig_message["trashed"]
        and not member.guild_permissions.manage_messages
    ):
        try:
            await member.send(t_("You cannot save a trashed message."))
        except discord.Forbidden:
            pass
        return
    message = await bot.cache.fetch_message(
        orig_message["guild_id"],
        orig_message["channel_id"],
        orig_message["id"],
    )
    if not message:
        return
    embed, attachments = await starboard_funcs.embed_message(bot, message)
    try:
        await member.send(embed=embed, files=attachments)
    except discord.Forbidden:
        pass
    return True


def setup(bot: Bot) -> None:
    bot.add_cog(QAEvents(bot))
