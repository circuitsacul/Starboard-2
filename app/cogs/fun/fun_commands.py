import random
from typing import List

import discord
from discord.ext import commands, flags

from app import converters, utils
from app.classes.bot import Bot
from app.cogs.starboard import starboard_funcs


class Fun(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    @flags.add_flag("--by", type=discord.User)
    @flags.add_flag("--in", type=discord.TextChannel)
    @flags.add_flag("--starboard", "--sb", type=converters.Starboard)
    @flags.command(name="moststarred", brief="Shows the most starred messages")
    @commands.guild_only()
    @commands.cooldown(1, 3, type=commands.BucketType.user)
    async def moststarred(self, ctx: commands.Context, **options) -> None:
        """See a list of the moststarred messages.

        Options:
            --by: Search for messages by this person
            --in: Search for messages sent in this channel
            --starboard: Search for messages that appeard on this starboard

        Example:
            sb!moststarred --by @Circuit --in #general --starboard #starboard
        """
        starboard_id = (
            options["starboard"].id if options["starboard"] else None
        )
        author_id = options["by"].id if options["by"] else None
        channel_id = options["in"].id if options["in"] else None

        messages = await self.bot.db.fetch(
            """SELECT * FROM starboard_messages
            WHERE ($1::numeric is NULL or starboard_id=$1::numeric)
            AND EXISTS(
                SELECT * FROM messages
                WHERE id=orig_id
                AND guild_id=$4
                AND ($2::numeric is NULL or author_id=$2::numeric)
                AND ($3::numeric is NULL or channel_id=$3::numeric)
                AND trashed=False
            ) ORDER BY points DESC""",
            starboard_id,
            author_id,
            channel_id,
            ctx.guild.id,
        )
        if len(messages) == 0:
            await ctx.send("Nothing to show.")
            return
        embeds: List[discord.Embed] = []
        text_pages: List[str] = []
        for m in messages[0:10]:
            orig = await self.bot.db.get_message(m["orig_id"])
            obj = await self.bot.cache.fetch_message(
                self.bot,
                ctx.guild.id,
                int(orig["channel_id"]),
                int(orig["id"]),
            )
            sql_starboard = await self.bot.db.get_starboard(m["starboard_id"])
            color = sql_starboard["color"]
            text_pages.append(
                starboard_funcs.get_plain_text(
                    sql_starboard, orig, m["points"], ctx.guild
                )
            )
            if not obj:
                continue
            e, _ = await starboard_funcs.embed_message(
                self.bot, obj, color=color
            )
            embeds.append(e)

        await utils.paginator(ctx, embeds, text_pages=text_pages)

    @flags.add_flag("--by", type=discord.User, default=None)
    @flags.add_flag("--in", type=discord.TextChannel, default=None)
    @flags.add_flag(
        "--starboard", "--sb", type=converters.Starboard, default=None
    )
    @flags.add_flag("--points", type=int, default=0)
    @flags.command(
        name="random",
        aliases=["explore", "rand"],
        brief="Shows a random starred message from the server",
    )
    @commands.guild_only()
    @commands.cooldown(3, 5, type=commands.BucketType.user)
    async def random_message(self, ctx: commands.Context, **options):
        """Pulls a random message from one of the starboards
        on the current server. Does NOT work cross-server.

        Options:
            --by: Only show messages authored by this person
            --in: Only show messages that were originaly sent
                in this channel
            --sb: Only show messages from this starboard
            --points: Only show messages that have at least
                this many points

        Examples:
            sb!random --by @Circuit --sb super-starboard
            sb!random --points 15
        """
        author_id = options["by"].id if options["by"] else None
        channel_id = options["in"].id if options["in"] else None
        starboard_id = (
            options["starboard"].id if options["starboard"] else None
        )
        good_messages = await self.bot.db.fetch(
            """SELECT * FROM starboard_messages
            WHERE ($1::numeric is NULL or starboard_id=$1::numeric)
            AND ($2::smallint is NULL or points >= $2::smallint)
            AND EXISTS (
                SELECT * FROM messages
                WHERE id=orig_id
                AND trashed=False
                AND ($3::numeric is NULL or author_id=$3::numeric)
                AND ($4::numeric is NULL or channel_id=$4::numeric)
            )
            AND EXISTS (
                SELECT * FROM starboards
                WHERE id=starboard_id
                AND explore=True
            )""",
            starboard_id,
            options["points"],
            author_id,
            channel_id,
        )
        if len(good_messages) == 0:
            await ctx.send(
                "No messages were found that matched those requirements."
            )
            return
        choice = random.choice(good_messages)
        orig_sql_message = await self.bot.db.get_message(choice["orig_id"])
        sql_starboard = await self.bot.db.get_starboard(choice["starboard_id"])
        orig_message = await self.bot.cache.fetch_message(
            self.bot,
            ctx.guild.id,
            orig_sql_message["channel_id"],
            orig_sql_message["id"],
        )
        if not orig_message:
            await ctx.send("Something went wrong. Please try again.")
            return

        points = choice["points"]

        embed, attachments = await starboard_funcs.embed_message(
            self.bot, orig_message, color=sql_starboard["color"]
        )
        plain_text = starboard_funcs.get_plain_text(
            sql_starboard, orig_sql_message, points, ctx.guild
        )
        await ctx.send(plain_text, embed=embed, files=attachments)

    # Removed, as it is a copy of the command of another bot. Feel free to
    # Uncomment if you selfhost the bot.
    # @commands.command(
    #    name='starworthy', aliases=['worthy'],
    #    brief="Tells you how starworthy a message is"
    # )
    # @commands.guild_only()
    # async def starworthy(
    #    self, ctx: commands.Context,
    #    message: converters.MessageLink
    # ) -> None:
    #    """Tells you how starworthy a message is."""
    #    r = random.Random(message.id)
    #    worthiness: float = r.randrange(0, 100)
    #    await ctx.send(f"That message is {worthiness}% starworthy")

    @commands.command(name="save", brief="Saves a message to your DM's")
    @commands.guild_only()
    async def save(
        self, ctx: commands.Context, message: converters.MessageLink
    ) -> None:
        """Saves a message to your DM's"""
        orig_sql_message = await starboard_funcs.orig_message(
            self.bot, message.id
        )
        m = message
        if orig_sql_message:
            if orig_sql_message["trashed"]:
                await ctx.send("You cannot save a trashed message")
                return
            orig_message = await self.bot.cache.fetch_message(
                self.bot,
                int(orig_sql_message["guild_id"]),
                int(orig_sql_message["channel_id"]),
                int(orig_sql_message["id"]),
            )
            if not orig_message:
                await ctx.send(
                    "That message was deleted, so you can't save it."
                )
                return
            m = orig_message
        embed, attachments = await starboard_funcs.embed_message(self.bot, m)
        try:
            await ctx.author.send(embed=embed, files=attachments)
        except discord.Forbidden:
            await ctx.send("I can't DM you, so you can't save that message.")


def setup(bot: Bot) -> None:
    bot.add_cog(Fun(bot))
