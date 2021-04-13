from typing import Optional

import discord
from discord.ext import commands

from app import errors
from app.classes.bot import Bot
from app.i18n import locales, t_


class Profile(commands.Cog):
    """Manage personal settings"""

    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.command(
        name="language", aliases=["lang", "locale"], brief="Sets your language"
    )
    async def set_user_language(
        self, ctx: commands.Context, locale: Optional[str]
    ):
        """Sets your personal language. Run without any input to view
        a list of valid language codes"""
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
        """Whether or not your profile can be viewed by other users
        in the rank command."""
        await self.bot.db.users.edit(ctx.author.id, public=public)
        if public:
            await ctx.send(t_("Your profile is now public."))
        else:
            await ctx.send(t_("Your profile is no longer public."))

    @commands.command(
        name="profile",
        aliases=["me"],
        brief="Shows your settings.",
    )
    @commands.cooldown(1, 3, type=commands.BucketType.user)
    @commands.bot_has_permissions(embed_links=True)
    async def profile(self, ctx: commands.Context):
        """Shows settings for your account"""
        sql_user = await self.bot.db.users.get(ctx.author.id)

        embed = discord.Embed(
            title=str(ctx.author), color=self.bot.theme_color
        ).add_field(
            name=t_("Settings"),
            value=t_("Language: {0}\n" "Public Profile: {1}").format(
                sql_user["locale"], sql_user["public"]
            ),
            inline=False,
        )

        await ctx.send(embed=embed)


def setup(bot: Bot):
    bot.add_cog(Profile(bot))
