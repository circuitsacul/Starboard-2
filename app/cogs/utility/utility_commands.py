import discord
from discord.ext import commands, flags

from app.classes.bot import Bot
from app import converters
from app import utils
from app.cogs.starboard import starboard_funcs
from app import errors
from . import utility_funcs


class Utility(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    @commands.command(
        name='force',
        brief="Forced a message to certain starboards"
    )
    @commands.has_guild_permissions(manage_messages=True)
    async def force_message(
        self, ctx: commands.Context,
        message_link: converters.MessageLink,
        *starboards: converters.Starboard
    ) -> None:
        starboards = [int(s.sql_attributes['id']) for s in starboards]
        if len(starboards) == 0:
            await ctx.send("Force this message to all starboards?")
            if not await utils.confirm(ctx):
                await ctx.send("Cancelling")
                return
        orig_sql_message = await starboard_funcs.orig_message(
            self.bot, message_link.id
        )
        if orig_sql_message is None:
            await self.bot.db.create_message(
                message_link.id, message_link.guild.id,
                message_link.channel.id,
                message_link.author.id,
                message_link.channel.is_nsfw(),
            )
            orig_sql_message = await self.bot.db.get_message(
                message_link.id
            )

        await utility_funcs.handle_forcing(
            self.bot,
            orig_sql_message['id'],
            orig_sql_message['guild_id'],
            starboards, True
        )
        if len(starboards) == 0:
            await ctx.send("Message forced to all starboards")
        else:
            converted = [f"<#{s}>" for s in starboards]
            await ctx.send(f"Message forced to {', '.join(converted)}")

    @commands.command(
        name='unforce',
        brief="Unforces a message from certain starboards"
    )
    @commands.has_guild_permissions(manage_messages=True)
    async def unforce_message(
        self, ctx: commands.Context,
        message_link: converters.MessageLink,
        *starboards: converters.Starboard
    ) -> None:
        starboards = [int(s.sql_attributes['id']) for s in starboards]

        orig_sql_message = await starboard_funcs.orig_message(
            self.bot, message_link.id
        )
        if not orig_sql_message:
            await ctx.send(
                "That message does not exist in the database"
            )
        if orig_sql_message['id'] != message_link.id and len(starboards) == 0:
            await ctx.send(
                "The message you passed appears to be a starboard "
                "message. Would you like to unforce this message "
                f"from {message_link.channel.mention} instead?"
            )
            if await utils.confirm(ctx):
                starboards = [message_link.channel.id]

        if len(starboards) == 0:
            await ctx.send("Unforce this message from all starboards?")
            if not await utils.confirm(ctx):
                await ctx.send("Cancelling")
                return
        await utility_funcs.handle_forcing(
            self.bot,
            orig_sql_message['id'],
            orig_sql_message['guild_id'],
            starboards, False
        )
        if len(starboards) == 0:
            await ctx.send("Message unforced from all starboards")
        else:
            converted = [f"<#{s}>" for s in starboards]
            await ctx.send(f"Message unforced from {', '.join(converted)}")

    @commands.command(
        name='trash',
        brief="Trashes a message so it can't be viewed"
    )
    @commands.has_guild_permissions(manage_messages=True)
    async def trash_message(
        self, ctx: commands.Context,
        message_link: converters.MessageLink
    ) -> None:
        orig_sql_message = await starboard_funcs.orig_message(
            self.bot, message_link.id
        )
        if not orig_sql_message:
            raise errors.DoesNotExist(
                "That message has not been starred, so I "
                "can't trash it."
            )
        await utility_funcs.handle_trashing(
            self.bot, orig_sql_message['id'], orig_sql_message['guild_id'],
            True
        )
        await ctx.send("Message trashed")

    @commands.command(
        name='untrash',
        brief="Untrashes a message"
    )
    @commands.has_guild_permissions(manage_messages=True)
    async def untrash_message(
        self, ctx: commands.Context,
        message_link: converters.MessageLink
    ) -> None:
        orig_sql_message = await starboard_funcs.orig_message(
            self.bot, message_link.id
        )
        if not orig_sql_message:
            raise errors.DoesNotExist(
                "That message does not exist in the database."
            )
        await utility_funcs.handle_trashing(
            self.bot, orig_sql_message['id'], orig_sql_message['guild_id'],
            False
        )
        await ctx.send("Message untrashed")

    @commands.command(
        name='trashcan', aliases=['trashed'],
        brief="Shows a list of trashed messages"
    )
    @commands.has_guild_permissions(manage_messages=True)
    async def show_trashcan(
        self, ctx: commands.Context
    ) -> None:
        trashed_messages = await self.bot.db.fetch(
            """SELECT * FROM messages
            WHERE guild_id=$1 AND trashed=True""",
            ctx.guild.id
        )
        if len(trashed_messages) == 0:
            await ctx.send("You have no trashed messages.")
            return
        p = commands.Paginator(prefix='', suffix='', max_size=2000)
        for m in trashed_messages:
            link = utils.jump_link(
                m['id'], m['channel_id'],
                m['guild_id']
            )
            p.add_line(
                f"**[{m['channel_id']}-{m['id']}]({link})**"
            )
        embeds = [
            discord.Embed(
                title="Trashed Messages",
                description=page,
                color=self.bot.theme_color
            ) for page in p.pages
        ]
        await utils.paginator(ctx, embeds)

    @flags.add_flag("--by", type=discord.User)
    @flags.add_flag("--notby", type=discord.User)
    @flags.add_flag("--contains", type=str)
    @flags.command(
        name='purge',
        brief="Trashes a large number of messages at once"
    )
    @commands.has_guild_permissions(manage_messages=True)
    async def purgetrash(
        self, ctx: commands.Context,
        limit: int, **flags
    ) -> None:
        if limit > 200:
            raise discord.InvalidArgument(
                "Can only purge up to 200 messages at once"
            )
        elif limit < 1:
            raise discord.InvalidArgument(
                "Must purge at least 1 message"
            )

        purged = {}
        total = 0

        def check(m: discord.Message) -> bool:
            if flags['by'] and m.author.id != flags['by'].id:
                return False
            if flags['notby'] and m.author.id == flags['notby'].id:
                return False
            if flags['contains'] and flags['contains'] not in m.content:
                return False
            return True

        async for m in ctx.channel.history(limit=limit):
            if not check(m):
                continue
            sql_message = await starboard_funcs.orig_message(
                self.bot, m.id
            )
            if not sql_message:
                continue
            await utility_funcs.handle_trashing(
                self.bot, sql_message['id'],
                sql_message['guild_id'], True
            )
            purged.setdefault(m.author, 0)
            purged[m.author] += 1
            total += 1

        embed = discord.Embed(
            title=f"Purged {total} Messages",
            description='\n'.join([
                f"{u.name}: {c}"
                for u, c in purged.items()
            ]),
            color=self.bot.theme_color
        )

        await ctx.send(embed=embed)


def setup(bot: Bot) -> None:
    bot.add_cog(Utility(bot))
