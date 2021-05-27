from typing import TYPE_CHECKING, List, Tuple

import discord
from discord.ext.prettyhelp import bot_has_permissions, has_guild_permissions

from app import commands, converters, errors
from app.classes.context import MyContext
from app.i18n import t_

if TYPE_CHECKING:
    from app.classes.bot import Bot


class AwardRoles(commands.Cog, description=t_("Manage AwardRoles.", True)):
    def __init__(self, bot: "Bot"):
        self.bot = bot

    @commands.group(
        name="posroles",
        aliases=["proles"],
        help=t_(
            "View and manage PosRoles for your server.\n"
            "(PosRoles stands for Position-based Award Roles)",
            True,
        ),
        invoke_without_command=True,
    )
    @bot_has_permissions(embed_links=True)
    async def posroles(self, ctx: "MyContext"):
        _posroles = await self.bot.db.posroles.get_many(ctx.guild.id)
        if len(_posroles) == 0:
            await ctx.send(t_("This server has no PosRoles set."))
            return
        pr: List[Tuple[discord.Role, int, int]] = [
            (
                role := ctx.guild.get_role(r["role_id"]),
                r["max_users"],
                role.position,
            )
            for r in _posroles
        ]
        pr.sort(key=lambda r: r[2], reverse=True)

        sql_guild = await self.bot.db.guilds.get(ctx.guild.id)
        string = (
            t_("Stack PosRoles: **{}**").format(sql_guild["stack_pos_roles"])
            + "\n\n"
            + "\n".join(f"{name}: **{req}**" for name, req, _ in pr)
        )
        embed = discord.Embed(
            title=t_("PosRoles"),
            description=string,
            color=self.bot.theme_color,
        )
        await ctx.send(embed=embed)

    @posroles.command(
        name="stack", help=t_("Whether or not to stack PosRoles.", True)
    )
    @has_guild_permissions(manage_roles=True)
    @commands.guild_only()
    async def set_posrole_stack(
        self,
        ctx: "MyContext",
        stack: converters.mybool,
    ):
        await self.bot.db.guilds.set_posrole_stack(ctx.guild.id, stack)
        if stack:
            await ctx.send(t_("PosRoles will be stacked from now on."))
        else:
            await ctx.send(t_("I will no longer stack PosRoles."))

    @posroles.command(
        name="add", aliases=["a"], help=t_("Adds a PosRole.", True)
    )
    @has_guild_permissions(manage_roles=True)
    @commands.guild_only()
    async def add_posrole(
        self,
        ctx: "MyContext",
        role: converters.Role,
        max_users: converters.myint,
    ):
        pr = await self.bot.db.posroles.get(role.id)
        if pr:
            raise errors.PosRoleAlreadyExists(role.name)

        await self.bot.db.posroles.create(role.id, ctx.guild.id, max_users)
        await ctx.send(t_("Created PosRole **{0}**.").format(role.name))

    @posroles.command(
        name="remove",
        aliases=["delete", "del", "d", "r"],
        help=t_("Removes a PosRole.", True),
    )
    @has_guild_permissions(manage_roles=True)
    @commands.guild_only()
    async def remove_posrole(
        self,
        ctx: "MyContext",
        posrole: converters.PosRole,
    ):
        await self.bot.db.posroles.delete(posrole.obj.id)
        await ctx.send(t_("Deleted PosRole **{0}**.").format(posrole.obj.name))

    @posroles.command(
        name="set",
        aliases=["maxusers"],
        help=t_("Sets the max users for a PosRole.", True),
    )
    @has_guild_permissions(manage_roles=True)
    @commands.guild_only()
    async def set_posrole_users(
        self,
        ctx: "MyContext",
        posrole: converters.PosRole,
        max_users: converters.myint,
    ):
        await self.bot.db.posroles.set_max_users(posrole.obj.id, max_users)
        await ctx.send(
            t_("Set the maximum users for the PosRole **{0}** to {1}.").format(
                posrole.obj.name,
                max_users,
            )
        )

    @commands.group(
        name="xproles",
        aliases=["xpr"],
        help=t_("View and manage XPRoles for your server.", True),
        invoke_without_command=True,
    )
    @bot_has_permissions(embed_links=True)
    @commands.guild_only()
    async def xproles(self, ctx: "MyContext"):
        _xproles = await self.bot.db.xproles.get_many(ctx.guild.id)
        if len(_xproles) == 0:
            await ctx.send(t_("This server has no XP Roles."))
            return
        xpr: List[Tuple[discord.Role, int]] = [
            (ctx.guild.get_role(r["role_id"]), r["required"]) for r in _xproles
        ]
        xpr.sort(key=lambda r: r[1], reverse=True)
        sql_guild = await self.bot.db.guilds.get(ctx.guild.id)
        string = (
            t_("Stack XPRoles: **{}**").format(sql_guild["stack_xp_roles"])
            + "\n\n"
            + "\n".join(f"{name}: **{req}**" for name, req in xpr)
        )

        embed = discord.Embed(
            title=t_("XP Roles"),
            description=string,
            color=self.bot.theme_color,
        )
        await ctx.send(embed=embed)

    @xproles.command(
        name="stack", help=t_("Whether or not to stack XPRoles.", True)
    )
    @has_guild_permissions(manage_roles=True)
    async def set_xprole_stacking(
        self,
        ctx: "MyContext",
        stack: converters.mybool,
    ):
        await self.bot.db.guilds.set_xprole_stack(ctx.guild.id, stack)
        if stack:
            await ctx.send(t_("XPRoles will be stacked from now on."))
        else:
            await ctx.send(t_("I will no longer stack XPRoles."))

    @xproles.command(
        name="add", aliases=["a"], help=t_("Adds an XPRole.", True)
    )
    @has_guild_permissions(manage_roles=True)
    @commands.guild_only()
    async def add_xprole(
        self,
        ctx: "MyContext",
        role: converters.Role,
        required: converters.myint,
    ):
        xpr = await self.bot.db.xproles.get(role.id)
        if xpr:
            raise errors.XpRoleAlreadyExists(role.name)

        await self.bot.db.xproles.create(role.id, ctx.guild.id, required)
        await ctx.send(t_("Created XPRole **{0}**.").format(role.name))

    @xproles.command(
        name="remove", aliases=["r"], help=t_("Removes an XPRole.", True)
    )
    @has_guild_permissions(manage_roles=True)
    @commands.guild_only()
    async def remove_xprole(self, ctx: "MyContext", xprole: converters.XPRole):
        await self.bot.db.xproles.delete(xprole.obj.id)
        await ctx.send(
            t_("Deleted the XPRole **{0}**.").format(xprole.obj.name)
        )

    @xproles.command(
        name="set",
        aliases=["required"],
        help=t_("Sets the ammount of xp needed to gain an XPRole.", True),
    )
    @has_guild_permissions(manage_roles=True)
    @commands.guild_only()
    async def set_xprole_required(
        self,
        ctx: "MyContext",
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
