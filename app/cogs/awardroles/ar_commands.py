import typing

import discord
from discord.ext import commands

from app import converters, errors
from app.i18n import t_

if typing.TYPE_CHECKING:
    from app.classes.bot import Bot


class AwardRoles(commands.Cog):
    def __init__(self, bot: "Bot"):
        self.bot = bot

    @commands.group(
        name="xproles",
        aliases=["xpr"],
        brief="View and manage XPRoles for your server.",
        invoke_without_command=True,
    )
    @commands.has_guild_permissions(manage_roles=True)
    @commands.bot_has_permissions(
        embed_links=True,
    )
    @commands.guild_only()
    async def xproles(self, ctx: commands.Context):
        """View and manage XPRoles for a guild"""
        _xproles = await self.bot.db.xproles.get_many(ctx.guild.id)
        if len(_xproles) == 0:
            await ctx.send(t_("This server has no XP Roles."))
            return
        xpr: list[tuple[discord.Role, int]] = [
            (ctx.guild.get_role(r["role_id"]), r["required"]) for r in _xproles
        ]
        xpr.sort(key=lambda r: r[1], reverse=True)
        string = "\n".join(f"{name}: **{req}**" for name, req in xpr)

        embed = discord.Embed(
            title=t_("XP Roles"),
            description=string,
            color=self.bot.theme_color,
        )
        await ctx.send(embed=embed)

    @xproles.command(name="add", aliases=["a"], brief="Adds an XPRole")
    @commands.has_guild_permissions(manage_roles=True)
    @commands.guild_only()
    async def add_xprole(
        self,
        ctx: commands.Context,
        role: discord.Role,
        required: converters.myint,
    ):
        xpr = await self.bot.db.xproles.get(role.id)
        if xpr:
            raise errors.XpRoleAlreadyExists(role.name)

        await self.bot.db.xproles.create(role.id, ctx.guild.id, required)
        await ctx.send(t_("Created XPRole **{0}**.").format(role.name))

    @xproles.command(name="remove", aliases=["r"], brief="Removes an XpRole")
    @commands.has_guild_permissions(manage_roles=True)
    @commands.guild_only()
    async def remove_xprole(
        self, ctx: commands.Context, xprole: converters.XPRole
    ):
        await self.bot.db.xproles.delete(xprole.obj.id)
        await ctx.send(
            t_("Deleted the XPRole **{0}**.").format(xprole.obj.name)
        )

    @xproles.command(
        name="set",
        aliases=["required"],
        brief="Sets the ammount of xp needed to gain an XPRole",
    )
    @commands.has_guild_permissions(manage_roles=True)
    @commands.guild_only()
    async def set_xprole_required(
        self,
        ctx: commands.Context,
        xprole: converters.XPRole,
        required: converters.myint,
    ):
        await self.bot.db.xproles.set_required(xprole.obj.id, required)
        await ctx.send(
            t_("Set the needed xp to {0} for the XPRole **{1}**.").format(
                required, xprole.obj.name
            )
        )


def setup(bot: "Bot"):
    bot.add_cog(AwardRoles(bot))
