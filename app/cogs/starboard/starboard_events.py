import discord

from app import commands, utils
from app.classes.bot import Bot
from app.cogs.utility import utility_funcs
from app.i18n import t_

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
        starboard = await self.bot.db.starboards.get(channel.id)
        if not starboard:
            return
        await self.bot.db.starboards.delete(channel.id)
        async with self.bot.temp_locale(channel.guild):
            self.bot.dispatch(
                "guild_log",
                t_("`{0}` was deleted, so I removed that starboard.").format(
                    channel.name
                ),
                "info",
                channel.guild,
            )

    @commands.Cog.listener()
    async def on_raw_message_delete(
        self, payload: discord.RawMessageDeleteEvent
    ) -> None:
        if payload.guild_id is None:
            return
        sb_message = await self.bot.db.sb_messages.get(payload.message_id)
        if sb_message:
            # Delete the starboard message
            await self.bot.db.sb_messages.delete(sb_message["id"])

            # Trash the message
            await utility_funcs.handle_trashing(
                self.bot,
                sb_message["orig_id"],
                payload.guild_id,
                True,
                reason=t_(
                    "Starboard message was deleted, so I autotrashed it."
                ),
            )
        else:
            await starboard_funcs.update_message(
                self.bot,
                payload.message_id,
                payload.guild_id,
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

        # Create necessary data
        await self.bot.db.users.create(payload.member.id, payload.member.bot)
        await self.bot.db.members.create(payload.member.id, payload.guild_id)

        # Get/create the message
        sql_message = await starboard_funcs.orig_message(
            self.bot, payload.message_id
        )
        if sql_message:
            guild_id, channel_id, message_id = (
                int(sql_message["guild_id"]),
                int(sql_message["channel_id"]),
                int(sql_message["id"]),
            )
        else:
            guild_id, channel_id, message_id = (
                payload.guild_id,
                payload.channel_id,
                payload.message_id,
            )
        try:
            message = await self.bot.cache.fetch_message(
                guild_id, channel_id, message_id
            )
        except discord.Forbidden:
            return

        if sql_message:
            author_id = int(sql_message["author_id"])
        elif message:
            author_id = message.author.id
        else:
            return

        guild = self.bot.get_guild(payload.guild_id)

        _author = await self.bot.cache.get_members([author_id], guild)
        if author_id not in _author:
            author_roles = []
        else:
            author_roles = [r.id for r in _author[author_id].roles]

        if not sql_message:
            # Create message + needed data
            await self.bot.db.users.create(
                message.author.id, message.author.bot
            )
            await self.bot.db.members.create(
                message.author.id, payload.guild_id
            )
            await self.bot.db.messages.create(
                message.id,
                message.guild.id,
                message.channel.id,
                message.author.id,
                message.channel.is_nsfw(),
            )

        sql_author = await self.bot.db.users.get(author_id)

        # Check if valid
        frozen = trashed = False
        if sql_message:
            frozen = sql_message["frozen"]
            trashed = sql_message["trashed"]
        valid, remove = await starboard_funcs.can_add(
            self.bot,
            emoji,
            payload.guild_id,
            payload.member,
            channel_id,
            sql_author,
            author_roles,
            frozen,
            trashed,
        )
        if remove:
            channel: discord.TextChannel = guild.get_channel(
                payload.channel_id
            )
            p_message = channel.get_partial_message(payload.message_id)
            try:
                await p_message.remove_reaction(payload.emoji, payload.member)
            except discord.Forbidden:
                pass
            return
        if not valid:
            return

        # Create the reaction
        await self.bot.db.reactions.create_reaction_user(
            emoji, message_id, payload.user_id
        )
        await starboard_funcs.update_message(
            self.bot, message_id, payload.guild_id
        )

        self.bot.dispatch(
            "star_update",
            payload.member.id,
            author_id,
            payload.guild_id,
            payload.channel_id,
            1,
        )

    @commands.Cog.listener()
    async def on_raw_reaction_remove(
        self, payload: discord.RawReactionActionEvent
    ) -> None:
        if not payload.guild_id:
            return
        emoji = utils.clean_emoji(payload.emoji)

        sb_emojis = []
        starboards = await self.bot.db.starboards.get_many(payload.guild_id)
        for s in starboards:
            sb_emojis += s["star_emojis"]
        if emoji not in sb_emojis:
            return

        orig_message = await starboard_funcs.orig_message(
            self.bot, payload.message_id
        )
        if orig_message is None:
            return

        if orig_message["frozen"] or orig_message["trashed"]:
            return

        r_user = await self.bot.db.reactions.get_reaction_user(
            emoji, int(orig_message["id"]), payload.user_id
        )
        if not r_user:
            return
        await self.bot.db.reactions.delete_reaction_user(
            emoji, int(orig_message["id"]), payload.user_id
        )
        await starboard_funcs.update_message(
            self.bot, orig_message["id"], payload.guild_id
        )

        self.bot.dispatch(
            "star_update",
            payload.user_id,
            orig_message["author_id"],
            payload.guild_id,
            payload.channel_id,
            -1,
        )


def setup(bot: Bot) -> None:
    bot.add_cog(StarboardEvents(bot))
