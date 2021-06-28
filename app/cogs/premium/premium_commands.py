from typing import TYPE_CHECKING, Literal, Tuple, Union

import discord
import humanize

import config
from app import buttons, checks, commands, constants
from app.classes.context import MyContext
from app.cogs.premium.premium_funcs import normal_limit_for, premium_limit_for
from app.i18n import t_

from . import premium_funcs

if TYPE_CHECKING:
    from app.classes.bot import Bot


def pvsn(key: str) -> Union[Tuple[int, int], Literal[False]]:
    prem, norm = premium_limit_for(key), normal_limit_for(key)
    if prem == norm:
        return False
    return norm, prem


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
            "Uses some of your credits to give the current server premium.",
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

    @commands.command(
        name="premium",
        aliases=["premiuminfo"],
        help=t_("Shows info on premium.", True),
    )
    async def show_premium_info(self, ctx: "MyContext"):
        info = t_(
            "We use a credit system for premium. It works like discord boosts "
            "-- every $ you send to us gives you 1 premium credit, and once "
            "you have 3 credits you can convert that to 1 month of premium "
            "for 1 server. You can gain credits by donating, or by becoming "
            "a patron (which will give you X credits/month, depending on your "
            "tier)."
        )
        keys = {
            "starboards": t_("Up to {0} starboards instead of {1}."),
            "sbemojis": t_("Up to {0} emojis per starboard instead of {1}."),
            "aschannels": t_("Up to {0} AutoStar channels instead of {1}."),
            "asemojis": t_(
                "Up to {0} emojis per AutoStar channel instead of {1}."
            ),
            "xproles": t_("Up to {0} XPRoles instead of {1}."),
            "posroles": t_("Up to {0} PosRoles instead of {1}."),
            "permgroups": t_("Up to {0} PermGroups instead of {1}."),
            "permroles": t_(
                "Up to {1} PermRoles per PermGroup instead of {1}."
            ),
        }
        perks = t_("**Premium Perks:**")
        for key, text in keys.items():
            norm, prem = normal_limit_for(key), premium_limit_for(key)
            if norm == prem:
                continue
            perks += "\n" + text.format(prem, norm)
        text = info + "\n\n" + perks
        await ctx.send(
            embed=discord.Embed(
                title=t_("Premium Info"),
                description=text,
                color=self.bot.theme_color,
            ).add_field(
                name=constants.ZWS,
                value=t_("Use `sb!profile` to view your credits."),
            )
        )

    @commands.group(
        name="autoredeem",
        help=t_(
            "Manage AutoRedeem for servers.\n"
            "If run in DMs, will show all servers AutoRedeem is enabled for."
        ),
        invoke_without_command=True,
    )
    async def autoredeem(self, ctx: "MyContext"):
        if ctx.guild is None:
            all_autoredeem = await self.bot.db.autoredeem.get_user_guilds(
                ctx.author.id
            )
            if len(all_autoredeem) == 0:
                await ctx.send(
                    t_("You don't have AutoRedeem enabled on any servers.")
                )
                return
            p = commands.Paginator(prefix="", suffix="")
            for ar in all_autoredeem:
                g = self.bot.get_guild(int(ar["guild_id"]))
                if g:
                    p.add_line(g.name + f" (`{g.id}`)")
                else:
                    p.add_line(t_("Unknown Guild (`{0}`)").format(g.id))
            embeds = [
                discord.Embed(
                    title="AutoRedeem",
                    description=page,
                    color=self.bot.theme_color,
                )
                for page in p.pages
            ]
            paginator = buttons.Paginator(ctx, embed_pages=embeds)
            await paginator.start()
        else:
            enabled = bool(
                await self.bot.db.autoredeem.get(ctx.guild.id, ctx.author.id)
            )
            if enabled:
                await ctx.send(t_("AutoRedeem is enabled for this server."))
            else:
                await ctx.send(t_("AutoRedeem is disabled for this server."))

    @autoredeem.command(
        name="enable",
        aliases=["on"],
        help=t_("Enable AutoRedeem for the current server."),
    )
    @commands.guild_only()
    async def enabled_autoredeem(self, ctx: "MyContext"):
        conf = await buttons.Confirm(
            ctx,
            t_(
                "Are you sure? When this server runs out of premium, "
                "credits will automatically be taken from your account."
            ),
        ).start()
        if not conf:
            await ctx.send(t_("Cancelled."))
            return
        await self.bot.db.autoredeem.create(ctx.guild.id, ctx.author.id)
        await ctx.send(t_("AutoRedeem has been enabled for this server."))

    @autoredeem.command(
        name="disable",
        aliases=["off"],
        help=t_("Disable AutoRedeem for a specific server."),
    )
    async def disable_autoredeem(
        self, ctx: "MyContext", guild: discord.Guild = None
    ):
        guild = guild or ctx.guild
        if not guild:
            await ctx.send(
                t_(
                    "Please specify a guild or run this command in the guild "
                    "you want to disable AutoRedeem in."
                )
            )
            return
        conf = await buttons.Confirm(
            ctx,
            t_(
                "Are you sure? Credits will no longer be taken from "
                "your account if {0} runs out of premium."
            ).format(guild.name),
        ).start()
        if not conf:
            await ctx.send(t_("Cancelled."))
            return
        await self.bot.db.autoredeem.delete(guild.id, ctx.author.id)
        await ctx.send(
            t_("AutoRedeem has been disabled for {0}.").format(guild.name)
        )


def setup(bot: "Bot"):
    bot.add_cog(Premium(bot))
