import typing

import humanize

import config
from app import buttons, checks, commands
from app.classes.context import MyContext
from app.i18n import t_

from . import premium_funcs

if typing.TYPE_CHECKING:
    from app.classes.bot import Bot


class Premium(commands.Cog, description=t_("Premium related commands.", True)):
    def __init__(self, bot: "Bot"):
        self.bot = bot

    @commands.command(
        name="serverpremium",
        aliases=["guildpremium", "serverprem", "guildprem"],
        help=t_("Shows the servers current premium status.", True),
    )
    async def show_guild_prem_status(self, ctx: "MyContext"):
        guild = await self.bot.db.guilds.get(ctx.guild.id)
        if guild["premium_end"] is not None:
            message = t_("This server has premium until {0}.").format(
                humanize.naturaldate(guild["premium_end"])
            )
        else:
            message = t_("This server does not have premium currently.")
        await ctx.send(message)

    @commands.command(
        name="refreshroles", help=t_("Refresh your donor/patron roles.", True)
    )
    @checks.support_server()
    @commands.cooldown(1, 5, type=commands.BucketType.user)
    async def refresh_roles(self, ctx: "MyContext"):
        self.bot.dispatch("update_prem_roles", ctx.author.id)
        await ctx.send(t_("Your roles should update momentarily."))

    @commands.command(
        name="redeem",
        help=t_(
            "Uses some of your credits to give the current " "server premium.",
            True,
        ),
    )
    @commands.guild_only()
    @commands.cooldown(1, 3, type=commands.BucketType.user)
    async def redeem_credits(self, ctx: "MyContext", months: int = 1):
        credits = config.CREDITS_PER_MONTH * months
        conf = await buttons.Confirm(
            ctx,
            t_(
                "Are you sure you want to do this? "
                "This will cost you {0} credits "
                "and will give **{1}** {2} months of "
                "premium."
            ).format(credits, ctx.guild.name, months),
        ).start()
        if not conf:
            await ctx.send(t_("Cancelled."))
            return
        await premium_funcs.redeem_credits(
            self.bot.db, ctx.guild.id, ctx.author.id, months
        )
        await ctx.send(t_("Done."))


def setup(bot: "Bot"):
    bot.add_cog(Premium(bot))
