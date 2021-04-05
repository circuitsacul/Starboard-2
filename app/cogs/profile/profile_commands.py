from typing import Optional

import discord
from discord.ext import commands

from app import errors
from app.classes.bot import Bot
from app.i18n import locales, t_


class Profile(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.command(
        name="language", aliases=["lang", "locale"], brief="Sets your language"
    )
    async def set_user_language(
        self, ctx: commands.Context, locale: Optional[str]
    ):
        if not locale:
            await ctx.send(
                t_("Valid Language Codes:\n{0}").format("\n".join(locales))
            )
            return
        if locale not in locales:
            raise errors.InvalidLocale(locale)
        await self.bot.db.users.edit(ctx.author.id, locale=locale)
        if ctx.author.id in self.bot.locale_cache:
            self.bot.locale_cache[ctx.author.id] = locale
        await ctx.send(t_("Set your language to {0}.").format(locale))

    @commands.command(
        name="public",
        aliases=["visible"],
        brief="Whether or not your profile is visible to others.",
    )
    async def set_user_public(self, ctx: commands.Context, public: bool):
        await self.bot.db.users.edit(ctx.author.id, public=public)
        if public:
            await ctx.send(t_("Your profile is now public."))
        else:
            await ctx.send(t_("Your profile is no longer public."))

    @commands.command(
        name="profile",
        aliases=["me"],
        brief="Shows your global statistics and settings.",
    )
    @commands.cooldown(1, 3, type=commands.BucketType.user)
    @commands.bot_has_permissions(embed_links=True)
    async def profile(self, ctx: commands.Context):
        sql_user = await self.bot.db.users.get(ctx.author.id)
        total_stars, total_recv = await self.bot.db.fetchrow(
            """SELECT SUM(stars_given), SUM(stars_received) FROM members
            WHERE user_id=$1""",
            ctx.author.id,
        )

        embed = (
            discord.Embed(title=str(ctx.author), color=self.bot.theme_color)
            .add_field(
                name=t_("Settings"),
                value=t_("Language: {0}\n" "Public Profile: {1}").format(
                    sql_user["locale"], sql_user["public"]
                ),
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
            .set_thumbnail(url=ctx.author.avatar_url)
        )

        await ctx.send(embed=embed)


def setup(bot: Bot):
    bot.add_cog(Profile(bot))
