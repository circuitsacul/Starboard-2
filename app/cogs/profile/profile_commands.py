import discord
from discord.ext.prettyhelp import bot_has_permissions

from app import commands, converters, i18n, utils
from app.classes.bot import Bot
from app.classes.context import MyContext
from app.i18n import t_


class Profile(
    commands.Cog,
    description=t_("Manage personal settings.", True),
):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.command(
        name="language",
        aliases=["lang", "locale"],
        help=t_("Sets your language.", True),
    )
    async def set_user_language(
        self, ctx: "MyContext", *, locale: converters.language = None
    ):
        if not locale:
            await ctx.send(
                embed=i18n.language_embed(self.bot, utils.clean_prefix(ctx))
            )
            return

        code, name = locale

        await self.bot.db.users.edit(ctx.author.id, locale=code)
        if ctx.author.id in self.bot.locale_cache:
            self.bot.locale_cache[ctx.author.id] = code
        await ctx.send(t_("Set your language to {0}.").format(name))

    @commands.command(
        name="public",
        aliases=["visible"],
        help=t_("Whether or not your profile is visible to others.", True),
    )
    async def set_user_public(self, ctx: "MyContext", public: bool):
        await self.bot.db.users.edit(ctx.author.id, public=public)
        if public:
            await ctx.send(t_("Your profile is now public."))
        else:
            await ctx.send(t_("Your profile is no longer public."))

    @commands.command(
        name="profile",
        aliases=["me"],
        help=t_("Shows your settings.", True),
    )
    @commands.cooldown(1, 3, type=commands.BucketType.user)
    @bot_has_permissions(embed_links=True)
    async def profile(self, ctx: "MyContext"):
        sql_user = await self.bot.db.users.get(ctx.author.id)

        total = sql_user["donation_total"] + sql_user["last_patreon_total"]
        patron = (
            f"{sql_user['patron_status']}, "
            f"${sql_user['last_known_monthly']}/month "
            f"(${sql_user['last_patreon_total']})"
        )

        embed = (
            discord.Embed(title=str(ctx.author), color=self.bot.theme_color)
            .add_field(
                name=t_("Settings"),
                value=t_("Language: {0}\nPublic Profile: {1}").format(
                    sql_user["locale"], sql_user["public"]
                ),
                inline=False,
            )
            .add_field(
                name=t_("Premium Info"),
                value=(
                    f"Credits: {sql_user['credits']}\n"
                    f"Patron: {patron}\n"
                    f"Donations: ${sql_user['donation_total']}\n"
                    f"Total Support: ${total}\n"
                ),
            )
        )

        await ctx.send(embed=embed)


def setup(bot: Bot):
    bot.add_cog(Profile(bot))
