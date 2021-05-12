import typing

from discord.ext import commands

from app import checks
from app.classes.context import MyContext
from app.i18n import t_

if typing.TYPE_CHECKING:
    from app.classes.bot import Bot


class Premium(commands.Cog):
    def __init__(self, bot: "Bot"):
        self.bot = bot

    @commands.command(
        name="refreshroles", help=t_("Refresh your donor/patron roles.", True)
    )
    @checks.support_server()
    @commands.cooldown(1, 5, type=commands.BucketType.user)
    async def refresh_roles(self, ctx: "MyContext"):
        self.bot.dispatch("update_prem_roles", ctx.author.id)
        await ctx.send(t_("Your roles should update momentarily."))


def setup(bot: "Bot"):
    bot.add_cog(Premium(bot))
