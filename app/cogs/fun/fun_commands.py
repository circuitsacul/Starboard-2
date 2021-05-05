import random

import discord
from discord.ext import commands, flags

from app import converters, menus
from app.classes.bot import Bot
from app.cogs.starboard import starboard_funcs
from app.i18n import t_

from . import fun_funcs


class Fun(commands.Cog):
    "Fun commands for Starboard"

    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    @commands.command(
        name="leaderboard",
        aliases=["lb"],
        help=t_("Shows the servers top 200 users", True),
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

        if len(p.pages) == 0:
            await ctx.send("Nothing to show.")
            return

        embeds = [
            discord.Embed(
                title=t_("Leaderboard for {0}:").format(ctx.guild.name),
                description=page,
                color=self.bot.theme_color,
            )
            for page in p.pages
        ]

        await menus.Paginator(embeds=embeds).start(ctx)

    @commands.command(
        name="rank",
        aliases=["stats"],
        help=t_("Shows statistics for yourself or another user", True),
    )
    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    async def user_stats(
        self, ctx: commands.Context, user: discord.Member = None
    ) -> None:
        user: discord.Member = user or ctx.message.author
        sql_user = await self.bot.db.users.get(user.id)
        if not sql_user:
            await ctx.send(t_("**{0}** has no stats to show.").format(user))
            return
        if sql_user["public"] is False and user.id != ctx.message.author.id:
            await ctx.send(
                t_("That user has their profile set to private.").format(user)
            )
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

        total_stars, total_recv = await self.bot.db.fetchrow(
            """SELECT SUM(stars_given), SUM(stars_received) FROM members
            WHERE user_id=$1""",
            ctx.author.id,
        )

        embed = (
            discord.Embed(
                title=f"{user}",
                color=self.bot.theme_color,
            )
            .add_field(
                name=t_("Stats for {0}").format(ctx.guild),
                value=t_(
                    "Rank: **#{0}**\n"
                    "Stars Given: **{1}**\n"
                    "Stars Received: **{2}**\n"
                    "XP: **{3}**\n"
                    "Level: **{4}**"
                ).format(rank, stars_given, stars_recv, xp, level),
                inline=False,
            )
            .add_field(
                name=t_("Global Stats"),
                value=t_(
                    "Total Stars Given: **{0}**\n"
                    "Total Stars Received: **{1}**\n"
                    "Total Votes: **{2}**"
                ).format(total_stars, total_recv, sql_user["votes"]),
                inline=False,
            )
            .set_thumbnail(url=user.avatar_url)
        )
        await ctx.send(embed=embed)

    @flags.add_flag("--by", type=discord.User)
    @flags.add_flag("--in", type=discord.TextChannel)
    @flags.add_flag("--maxstars", "--maxpoints", type=converters.myint)
    @flags.add_flag("--starboard", "--sb", type=converters.Starboard)
    @flags.add_flag("--place", type=converters.myint, default=1)
    @flags.command(
        name="moststarred", help=t_("Shows the most starred messages", True)
    )
    @commands.cooldown(1, 10, type=commands.BucketType.user)
    @commands.bot_has_permissions(
        embed_links=True, add_reactions=True, read_message_history=True
    )
    @commands.guild_only()
    async def moststarred(self, ctx: commands.Context, **options) -> None:
        starboard_id = (
            options["starboard"].obj.id if options["starboard"] else None
        )
        all_starboards = [
            s["id"]
            for s in await self.bot.db.fetch(
                """SELECT * FROM starboards
                WHERE guild_id=$1
                AND explore=True""",
                ctx.guild.id,
            )
        ]
        author_id = options["by"].id if options["by"] else None
        channel_id = options["in"].id if options["in"] else None
        maxpoints = options["maxstars"]
        place = options["place"] - 1

        if place < 0:
            raise commands.BadArgument(t_("--place must be greater than 0"))

        messages = await self.bot.db.fetch(
            """SELECT * FROM starboard_messages
            WHERE starboard_id=any($1::numeric[])
            AND ($2::numeric is NULL or starboard_id=$2::numeric)
            AND EXISTS(
                SELECT * FROM messages
                WHERE id=orig_id
                AND ($3::numeric is NULL or author_id=$3::numeric)
                AND ($4::numeric is NULL or channel_id=$4::numeric)
                AND trashed=False
            )
            AND ($5::smallint is NULL or points <= $5::smallint)
            ORDER BY points DESC""",
            all_starboards,
            starboard_id,
            author_id,
            channel_id,
            maxpoints,
        )
        embeds: list[discord.Embed] = []
        text_pages: list[str] = []
        async with ctx.typing():
            for m in messages[place : place + 10]:
                orig = await self.bot.db.messages.get(m["orig_id"])
                obj = await self.bot.cache.fetch_message(
                    ctx.guild.id,
                    int(orig["channel_id"]),
                    int(orig["id"]),
                )
                sql_starboard = await self.bot.db.starboards.get(
                    m["starboard_id"]
                )
                color = sql_starboard["color"]
                if not obj:
                    continue
                e, _ = await starboard_funcs.embed_message(
                    self.bot, obj, color=color
                )
                text_pages.append(
                    starboard_funcs.get_plain_text(
                        sql_starboard, orig, m["points"], ctx.guild
                    )
                )
                embeds.append(e)

        if len(embeds) == 0:
            await ctx.send(t_("Nothing to show."))
            return

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
        help=t_("Shows a random starred message from the server", True),
    )
    @commands.cooldown(3, 5, type=commands.BucketType.user)
    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    async def random_message(self, ctx: commands.Context, **options):
        author_id = options["by"].id if options["by"] else None
        channel_id = options["in"].id if options["in"] else None
        starboard_id = (
            options["starboard"].obj.id if options["starboard"] else None
        )
        all_starboards = [
            s["id"]
            for s in await self.bot.db.fetch(
                """SELECT * FROM starboards
                WHERE guild_id=$1
                AND explore=True""",
                ctx.guild.id,
            )
        ]

        good_messages = await self.bot.db.fetch(
            """SELECT * FROM starboard_messages
            WHERE starboard_id=any($1::numeric[])
            AND ($2::numeric is NULL or starboard_id=$2::numeric)
            AND ($3::smallint is NULL or points >= $3::smallint)
            AND ($4::smallint is NULL or points <= $4::smallint)
            AND EXISTS (
                SELECT * FROM messages
                WHERE id=orig_id
                AND trashed=False
                AND ($5::numeric is NULL or author_id=$5::numeric)
                AND ($6::numeric is NULL or channel_id=$6::numeric)
            )""",
            all_starboards,
            starboard_id,
            options["points"],
            options["maxstars"],
            author_id,
            channel_id,
        )
        if len(good_messages) == 0:
            await ctx.send(
                t_("No messages were found that matched those requirements.")
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
            await ctx.send(t_("Something went wrong. Please try again."))
            return

        points = choice["points"]

        embed, attachments = await starboard_funcs.embed_message(
            self.bot, orig_message, color=sql_starboard["color"]
        )
        plain_text = starboard_funcs.get_plain_text(
            sql_starboard, orig_sql_message, points, ctx.guild
        )
        await ctx.send(plain_text, embed=embed, files=attachments)

    @commands.command(
        name="starworthy",
        aliases=["worthy"],
        help=t_("Tells you how starworthy a message is", True),
    )
    @commands.guild_only()
    async def starworthy(
        self, ctx: commands.Context, message: converters.GuildMessage
    ) -> None:
        r = random.Random(message.id)
        worthiness: float = r.randrange(0, 100)
        await ctx.send(
            t_("That message is {}% starworthy.").format(worthiness)
        )

    @commands.command(
        name="save", help=t_("Saves a message to your DM's", True)
    )
    @commands.guild_only()
    async def save(
        self, ctx: commands.Context, message: converters.GuildMessage
    ) -> None:
        orig_sql_message = await starboard_funcs.orig_message(
            self.bot, message.id
        )
        m = message
        if orig_sql_message:
            if orig_sql_message["trashed"]:
                await ctx.send(t_("You cannot save a trashed message."))
                return
            orig_message = await self.bot.cache.fetch_message(
                int(orig_sql_message["guild_id"]),
                int(orig_sql_message["channel_id"]),
                int(orig_sql_message["id"]),
            )
            if not orig_message:
                await ctx.send(
                    t_("That message was deleted, so you can't save it.")
                )
                return
            m = orig_message
        embed, attachments = await starboard_funcs.embed_message(self.bot, m)
        try:
            await ctx.author.send(embed=embed, files=attachments)
        except discord.Forbidden:
            await ctx.send(
                t_("I can't DM you, so you can't save that message.")
            )


def setup(bot: Bot) -> None:
    bot.add_cog(Fun(bot))
