import random
from typing import List

import discord
from discord.ext import commands, flags

from app import converters, menus
from app.classes.bot import Bot
from app.cogs.starboard import starboard_funcs

from . import fun_funcs


class Fun(commands.Cog):
    "Fun commands for Starboard"

    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    @commands.command(
        name="leaderboard",
        aliases=["lb"],
        brief="Shows the servers top 200 users",
    )
    @commands.bot_has_permissions(
        embed_links=True, add_reactions=True, read_message_history=True
    )
    @commands.guild_only()
    async def guild_leaderboard(self, ctx: commands.Context) -> None:
        leaderboard = await fun_funcs.get_guild_leaderboard(
            self.bot, ctx.guild
        )
        p = commands.Paginator(max_size=500)

        def build_string(u: dict) -> str:
            def setlen(text: str, new_length: int) -> str:
                length = len(text)
                if new_length > length:
                    return text + " " * (new_length - length)
                else:
                    return text[0 : new_length - 3] + "..."

            return (
                f"#{u['rank']}: {setlen(u['name'], 20)} "
                f"Level: {u['level']:02} XP: {u['xp']:04}"
            )

        for _uid, u in leaderboard.items():
            p.add_line(build_string(u))

        embeds = [
            discord.Embed(
                title=f"Leaderboard for {ctx.guild.name}",
                description=page,
                color=self.bot.theme_color,
            )
            for page in p.pages
        ]

        await menus.Paginator(embeds=embeds).start(ctx)

    @commands.command(
        name="rank",
        aliases=["stats"],
        brief="Shows statistics for yourself or another user",
    )
    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    async def user_stats(
        self, ctx: commands.Context, user: discord.Member = None
    ) -> None:
        user: discord.Member = user or ctx.message.author
        sql_user = await self.bot.db.users.get(user.id)
        if not sql_user:
            await ctx.send(f"**{user}** has no stats to show.")
            return
        sql_member = await self.bot.db.members.get(user.id, ctx.guild.id)

        # Guild Stats
        rank = await fun_funcs.get_rank(self.bot, ctx.guild, user.id)
        if sql_member:
            stars_given = sql_member["stars_given"]
            stars_recv = sql_member["stars_received"]
            xp = sql_member["xp"]
            level = sql_member["level"]
        else:
            stars_given = stars_recv = xp = level = 0

        embed = discord.Embed(
            title=f"{user}",
            description=(
                f"Rank: **#{rank}**\n"
                f"Stars Given: **{stars_given}**\n"
                f"Stars Received: **{stars_recv}**\n"
                f"XP: **{xp}**\n"
                f"Level: **{level}**"
            ),
            color=self.bot.theme_color,
        ).set_thumbnail(url=user.avatar_url)
        await ctx.send(embed=embed)

    @flags.add_flag("--by", type=discord.User)
    @flags.add_flag("--in", type=discord.TextChannel)
    @flags.add_flag("--maxstars", "--maxpoints", type=converters.myint)
    @flags.add_flag("--starboard", "--sb", type=converters.Starboard)
    @flags.add_flag("--place", type=converters.myint, default=1)
    @flags.command(name="moststarred", brief="Shows the most starred messages")
    @commands.cooldown(1, 3, type=commands.BucketType.user)
    @commands.bot_has_permissions(
        embed_links=True, add_reactions=True, read_message_history=True
    )
    @commands.guild_only()
    async def moststarred(self, ctx: commands.Context, **options) -> None:
        """See a list of the most starred messages.

        Options:
            --by: Search for messages by this person
            --in: Search for messages sent in this channel
            --maxstars: Search for messages that have fewer stars than this
            --starboard: Search for messages that appeard on this starboard
            --place: Start at a certain point in the list, instead of at the
                top

        Example:
            sb!moststarred --by @Circuit --in #general --starboard #starboard
        """
        starboard_id = (
            options["starboard"].obj.id if options["starboard"] else None
        )
        author_id = options["by"].id if options["by"] else None
        channel_id = options["in"].id if options["in"] else None
        maxpoints = options["maxstars"]
        place = options["place"] - 1

        if place < 0:
            raise commands.BadArgument("--place must be greater than 0")

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
            )
            AND EXISTS (
                SELECT * FROM starboards
                WHERE id=starboard_id
                AND explore=True
            )
            AND ($5::smallint is NULL or points <= $5::smallint)
            ORDER BY points DESC""",
            starboard_id,
            author_id,
            channel_id,
            ctx.guild.id,
            maxpoints,
        )
        if len(messages) == 0:
            await ctx.send("Nothing to show.")
            return
        embeds: List[discord.Embed] = []
        text_pages: List[str] = []
        for m in messages[place : place + 10]:
            orig = await self.bot.db.messages.get(m["orig_id"])
            obj = await self.bot.cache.fetch_message(
                ctx.guild.id,
                int(orig["channel_id"]),
                int(orig["id"]),
            )
            sql_starboard = await self.bot.db.starboards.get(m["starboard_id"])
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

        await menus.Paginator(
            embeds=embeds, text=text_pages, delete_after=True
        ).start(ctx)

    @flags.add_flag("--by", type=discord.User, default=None)
    @flags.add_flag("--in", type=discord.TextChannel, default=None)
    @flags.add_flag(
        "--starboard", "--sb", type=converters.Starboard, default=None
    )
    @flags.add_flag("--points", type=converters.myint)
    @flags.add_flag("--maxstars", "--maxpoints", type=converters.myint)
    @flags.command(
        name="random",
        aliases=["explore", "rand"],
        brief="Shows a random starred message from the server",
    )
    @commands.cooldown(3, 5, type=commands.BucketType.user)
    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
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
            --maxstars: Only show messages that have at most
                this many points

        Examples:
            sb!random --by @Circuit --sb super-starboard
            sb!random --points 15 --maxstars 50
        """
        author_id = options["by"].id if options["by"] else None
        channel_id = options["in"].id if options["in"] else None
        starboard_id = (
            options["starboard"].obj.id if options["starboard"] else None
        )
        good_messages = await self.bot.db.fetch(
            """SELECT * FROM starboard_messages
            WHERE ($1::numeric is NULL or starboard_id=$1::numeric)
            AND ($2::smallint is NULL or points >= $2::smallint)
            AND ($3::smallint is NULL or points <= $3::smallint)
            AND EXISTS (
                SELECT * FROM messages
                WHERE id=orig_id
                AND trashed=False
                AND ($4::numeric is NULL or author_id=$4::numeric)
                AND ($5::numeric is NULL or channel_id=$5::numeric)
            )
            AND EXISTS (
                SELECT * FROM starboards
                WHERE id=starboard_id
                AND explore=True
            )""",
            starboard_id,
            options["points"],
            options["maxstars"],
            author_id,
            channel_id,
        )
        if len(good_messages) == 0:
            await ctx.send(
                "No messages were found that matched those requirements."
            )
            return
        choice = random.choice(good_messages)
        orig_sql_message = await self.bot.db.messages.get(choice["orig_id"])
        sql_starboard = await self.bot.db.starboards.get(
            choice["starboard_id"]
        )
        orig_message = await self.bot.cache.fetch_message(
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
