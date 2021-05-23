import typing
from typing import Optional

import discord
from discord.ext import commands, flags
from discord.ext.prettyhelp import bot_has_permissions, has_guild_permissions

from app import converters, errors, menus, utils
from app.classes.context import MyContext
from app.i18n import t_

from . import pr_functions

if typing.TYPE_CHECKING:
    from app.classes.bot import Bot


class PermRoles(
    commands.Cog, description=t_("Manage PermRoles for a server.", True)
):
    def __init__(self, bot: "Bot"):
        self.bot = bot

    @flags.add_flag("--roles", type=discord.Role, nargs="+", default=[])
    @flags.add_flag("--starboard", "--sb", type=converters.Starboard)
    @flags.add_flag("--channel", type=discord.TextChannel)
    @flags.add_flag("--me", action="store_true")
    @flags.command(
        name="dummy",
        help=t_(
            "Tests the permissions of a fake user with certain roles.", True
        ),
    )
    @has_guild_permissions(manage_guild=True)
    @commands.guild_only()
    async def run_dummy_check(self, ctx, **options):
        if not options["me"]:
            roles = options["roles"]
            roles.insert(0, ctx.guild.default_role)
        else:
            roles = ctx.message.author.roles
        role_ids = [r.id for r in roles]
        channel = options["channel"].id if options["channel"] else None
        starboard = (
            options["starboard"].obj.id if options["starboard"] else None
        )
        perms = await pr_functions.get_perms(
            self.bot,
            role_ids,
            ctx.guild.id,
            channel,
            starboard,
        )
        embed = discord.Embed(
            title=t_("Dummy Check"),
            color=self.bot.theme_color,
            description=t_(
                "Channel: {0}\n" "Starboard: {1}\n" "Roles: {2}"
            ).format(
                options["channel"],
                options["starboard"],
                ", ".join(r.name for r in roles),
            ),
        ).add_field(
            name="Result", value=pr_functions.pretty_perm_string(perms)
        )
        await ctx.send(embed=embed)

    @commands.group(
        name="permgroups",
        aliases=["pg", "permroles", "pr"],
        help=t_("Lists PermGroups, or views settings for a PermGroup.", True),
        invoke_without_command=True,
    )
    @bot_has_permissions(embed_links=True)
    @commands.guild_only()
    async def permgroups(
        self,
        ctx: "MyContext",
        group: Optional[converters.PermGroup] = None,
    ):
        if not group:
            groups = await self.bot.db.permgroups.get_many(ctx.guild.id)
            if not groups:
                await ctx.send(t_("You have no PermGroups."))
            else:
                embed = discord.Embed(
                    title=t_("PermGroups for {0}").format(ctx.guild),
                    description="\n".join(
                        [f"{g['index']}. {g['name']}" for g in groups]
                    ),
                    color=self.bot.theme_color,
                )
                await ctx.send(embed=embed)
        else:
            p = utils.clean_prefix(ctx)
            embed = (
                discord.Embed(
                    title=f"PermGroup {group['name']}",
                    color=self.bot.theme_color,
                    description=t_(
                        "If you're looking for the PermRoles "
                        "of this PermGroup, run {0}."
                    ).format(f"`{p}pg roles {group['name']}`"),
                )
                .add_field(
                    name="channels",
                    value=utils.pretty_channel_string(
                        group["channels"], ctx.guild
                    ),
                )
                .add_field(
                    name="starboards",
                    value=utils.pretty_channel_string(
                        group["starboards"], ctx.guild
                    ),
                )
            )
            await ctx.send(embed=embed)

    @permgroups.command(name="add", help=t_("Add a PermGroup.", True))
    @bot_has_permissions(embed_links=True)
    @has_guild_permissions(manage_guild=True)
    @commands.guild_only()
    async def add_permgroup(self, ctx: "MyContext", name: str):
        await self.bot.db.permgroups.create(ctx.guild.id, name)
        await ctx.send(t_("Created PermGroup {0}").format(name))

    @permgroups.command(
        name="delete",
        aliases=["remove", "rm", "del"],
        help=t_("Deletes a PermGroup.", True),
    )
    @has_guild_permissions(manage_guild=True)
    @commands.guild_only()
    async def del_permgroup(
        self, ctx: "MyContext", group: converters.PermGroup
    ):
        await self.bot.db.permgroups.delete(group["id"])
        await ctx.send(t_("Deleted PermGroup **{0}**.").format(group["name"]))

    @permgroups.command(
        name="move", help=t_("Sets the position of a PermGroup.", True)
    )
    @has_guild_permissions(manage_guild=True)
    @commands.guild_only()
    async def move_permgroup(
        self,
        ctx: "MyContext",
        group: converters.PermGroup,
        position: converters.myint,
    ):
        new_index = await self.bot.db.permgroups.move(group["id"], position)
        await ctx.send(
            t_("Moved the PermGroup **{0}** from {1} to {2}.").format(
                group["name"], group["index"], new_index
            )
        )

    @permgroups.group(
        name="channels",
        aliases=["c"],
        help=t_("Manage the channels that a PermGroup affects.", True),
        invoke_without_command=True,
    )
    @has_guild_permissions(manage_guild=True)
    @commands.guild_only()
    async def pg_channels(self, ctx: "MyContext"):
        await ctx.send_help(ctx.command)

    @pg_channels.command(
        name="add",
        aliases=["a"],
        help=t_(
            "Adds channel(s) to the list of channels for a PermGroup.", True
        ),
    )
    @has_guild_permissions(manage_guild=True)
    @commands.guild_only()
    async def add_pg_channels(
        self,
        ctx: "MyContext",
        group: converters.PermGroup,
        *channels: discord.TextChannel,
    ):
        current_channels = set(int(cid) for cid in group["channels"])
        for c in channels:
            current_channels.add(c.id)
        current_channels = list(current_channels)

        await self.bot.db.permgroups.set_channels(
            group["id"], current_channels
        )
        await ctx.send(
            t_("Added {0} to the channels on PermGroup **{1}**.").format(
                ", ".join(c.mention for c in channels), group["name"]
            )
        )

    @pg_channels.command(
        name="remove",
        aliases=["rm", "r", "del", "delete"],
        help=t_(
            "Removes channel(s) from the list of channels on a PermGroup.",
            True,
        ),
    )
    @has_guild_permissions(manage_guild=True)
    @commands.guild_only()
    async def remove_pg_channels(
        self,
        ctx: "MyContext",
        group: converters.PermGroup,
        *channels: discord.TextChannel,
    ):
        current_channels = set(int(cid) for cid in group["channels"])
        for c in channels:
            current_channels.remove(c.id)
        current_channels = list(current_channels)

        await self.bot.db.permgroups.set_channels(
            group["id"], current_channels
        )
        await ctx.send(
            t_("Removed {0} from the channels on PermGroup **{1}**.").format(
                ", ".join(c.mention for c in channels), group["name"]
            )
        )

    @pg_channels.command(
        name="clear", help=t_("Clears all channels from a PermGroup.", True)
    )
    @has_guild_permissions(manage_guild=True)
    @commands.guild_only()
    async def clear_pg_channels(
        self, ctx: "MyContext", group: converters.PermGroup
    ):
        if not await menus.Confirm(
            t_(
                "Are you sure you want to clear all channels for "
                "the PermGroup **{0}**?"
            ).format(group["name"])
        ).start(ctx):
            await ctx.send(t_("Cancelled."))
            return

        await self.bot.db.permgroups.set_channels(group["id"], [])
        await ctx.send(
            t_("Cleared all channels for the PermGroup **{0}**.").format(
                group["name"]
            )
        )

    @permgroups.group(
        name="starboards",
        aliases=["s"],
        help=t_("Manage the starboards that a PermGroup affects.", True),
        invoke_without_command=True,
    )
    @has_guild_permissions(manage_guild=True)
    @commands.guild_only()
    async def pg_starboards(
        self,
        ctx: "MyContext",
    ):
        await ctx.send_help(ctx.command)

    @pg_starboards.command(
        name="add",
        aliases=["a"],
        help=t_(
            "Adds starboard(s) to the list of starboards for a PermGroup.",
            True,
        ),
    )
    @has_guild_permissions(manage_guild=True)
    @commands.guild_only()
    async def add_pg_starboards(
        self,
        ctx: "MyContext",
        group: converters.PermGroup,
        *starboards: converters.Starboard,
    ):
        current_starboards = set(int(sid) for sid in group["starboards"])
        for s in starboards:
            current_starboards.add(s.obj.id)
        current_starboards = list(current_starboards)
        await self.bot.db.permgroups.set_starboards(
            group["id"], current_starboards
        )
        await ctx.send(
            t_("Added {0} to the starboards on PermGroup **{1}**.").format(
                ", ".join(s.obj.mention for s in starboards), group["name"]
            )
        )

    @pg_starboards.command(
        name="remove",
        aliases=["r", "rm", "del", "delete"],
        help=t_(
            "Removes starboard(s) from the list "
            "of starboars on a PermGroup.",
            True,
        ),
    )
    @has_guild_permissions(manage_guild=True)
    @commands.guild_only()
    async def remove_pg_starboards(
        self,
        ctx: "MyContext",
        group: converters.PermGroup,
        *starboards: converters.Starboard,
    ):
        current_starboards = set(int(sid) for sid in group["starboards"])
        for s in starboards:
            current_starboards.remove(s.obj.id)
        current_starboards = list(current_starboards)
        await self.bot.db.permgroups.set_starboards(
            group["id"], current_starboards
        )
        await ctx.send(
            t_("Removed {0} from the starboards on PermGroup **{1}**.").format(
                ", ".join(s.obj.mention for s in starboards), group["name"]
            )
        )

    @pg_starboards.command(
        name="clear", help=t_("Clears all starboards on a PermGroup.", True)
    )
    @has_guild_permissions(manage_guild=True)
    @commands.guild_only()
    async def clear_pg_starboards(
        self, ctx: "MyContext", group: converters.PermGroup
    ):
        if not await menus.Confirm(
            t_(
                "Are you sure you want to clear all starboards "
                "for the PermGroup **{0}**?"
            ).format(group["name"])
        ).start(ctx):
            await ctx.send("Cancelled.")
            return

        await self.bot.db.permgroups.set_starboards(group["id"], [])
        await ctx.send(
            t_("Cleared all starboards for PermGroup **{0}**.").format(
                group["name"]
            )
        )

    @permgroups.group(
        name="roles",
        aliases=["permroles", "pr"],
        help=t_("Manage/View PermRoles for a PermGroup.", True),
        invoke_without_command=True,
    )
    @has_guild_permissions(manage_guild=True)
    @commands.guild_only()
    async def permroles(
        self,
        ctx: "MyContext",
        group: converters.PermGroup,
    ):
        permroles = await self.bot.db.permroles.get_many(group["id"])
        if not permroles:
            await ctx.send(
                t_("There are no PermRoles for the PermGroup **{0}**.").format(
                    group["name"]
                )
            )
            return
        embeds = []
        for role_group in utils.chunk_list(permroles, 9):
            embed = discord.Embed(
                title=t_("PermRoles for {0}").format(group["name"]),
                color=self.bot.theme_color,
            )
            for pr in role_group:
                name, value = pr_functions.pretty_permrole_string(
                    pr, ctx.guild
                )
                embed.add_field(name=name, value=value)
            embeds.append(embed)

        paginator = menus.Paginator(embeds, delete_after=True)
        await paginator.start(ctx)

    @permroles.command(
        name="add",
        aliases=["a"],
        help=t_("Adds a PermRole to a PermGroup.", True),
    )
    @has_guild_permissions(manage_guild=True)
    @commands.guild_only()
    async def add_permrole(
        self,
        ctx: "MyContext",
        group: converters.PermGroup,
        role: converters.Role,
    ):
        if (await self.bot.db.permroles.get(role.id, group["id"])) is not None:
            raise errors.PermRoleAlreadyExists(role.name, group["name"])

        await self.bot.db.permroles.create(group["id"], role.id)
        await ctx.send(
            t_("{0} is now a PermRole on the PermGroup **{1}**.").format(
                role.name, group["name"]
            )
        )

    @permroles.command(
        name="remove",
        aliases=["r", "rm", "del", "delete"],
        help=t_("Removes a PermRole from a PermGroup.", True),
    )
    @has_guild_permissions(manage_guild=True)
    @commands.guild_only()
    async def remove_permrole(
        self,
        ctx: "MyContext",
        group: converters.PermGroup,
        role: converters.PermRole(-1),
    ):
        await self.bot.db.permroles.delete(role.obj.id, group["id"])
        await ctx.send(
            t_("{0} is no longer a PermRole on the PermGroup **{1}**.").format(
                role.obj.name, group["name"]
            )
        )

    @permroles.command(
        name="move",
        help=t_("Changes the position of a PermRole in a PermGroup.", True),
    )
    @has_guild_permissions(manage_guild=True)
    @commands.guild_only()
    async def move_permrole(
        self,
        ctx: "MyContext",
        group: converters.PermGroup,
        role: converters.PermRole(-1),
        new_position: converters.myint,
    ):
        new_index = await self.bot.db.permroles.move(
            role.obj.id, group["id"], new_position
        )
        await ctx.send(
            t_("Moved the PermRole {0} from {1} to {2}.").format(
                role.name, role.sql["index"], new_index
            )
        )

    @permroles.command(
        name="allowCommands",
        aliases=["commands"],
        help=t_("Sets the allowCommands permission for a PermRole.", True),
    )
    @has_guild_permissions(manage_guild=True)
    @commands.guild_only()
    async def pr_allow_commands(
        self,
        ctx: "MyContext",
        group: converters.PermGroup,
        role: converters.PermRole(-1),
        allow_commands: converters.OrNone(converters.mybool),
    ):
        await self.bot.db.permroles.edit(
            role.obj.id, group["id"], allow_commands=allow_commands
        )
        await ctx.send(
            embed=utils.cs_embed(
                {
                    "allowCommnads": (
                        role.sql["allow_commands"],
                        allow_commands,
                    )
                },
                self.bot,
            )
        )

    @permroles.command(
        name="onStarboard",
        aliases=["starbaord"],
        help=t_("Sets the onStarboard permission for a PermRole.", True),
    )
    @has_guild_permissions(manage_guild=True)
    @commands.guild_only()
    async def pr_on_starboard(
        self,
        ctx: "MyContext",
        group: converters.PermGroup,
        role: converters.PermRole(-1),
        on_starboard: converters.OrNone(converters.mybool),
    ):
        await self.bot.db.permroles.edit(
            role.obj.id, group["id"], on_starboard=on_starboard
        )
        await ctx.send(
            embed=utils.cs_embed(
                {"onStarboard": (role.sql["on_starboard"], on_starboard)},
                self.bot,
            )
        )

    @permroles.command(
        name="giveStars",
        aliases=["give"],
        help=t_("Sets the giveStars permission for a PermRole.", True),
    )
    @has_guild_permissions(manage_guild=True)
    @commands.guild_only()
    async def pr_give_stars(
        self,
        ctx: "MyContext",
        group: converters.PermGroup,
        role: converters.PermRole(-1),
        give_stars: converters.OrNone(converters.mybool),
    ):
        await self.bot.db.permroles.edit(
            role.boj.id, group["id"], give_stars=give_stars
        )
        await ctx.send(
            embed=utils.cs_embed(
                {"giveStars": (role.sql["give_stars"], give_stars)}, self.bot
            )
        )

    @permroles.command(
        name="gainXP",
        aliases=["xp"],
        help=t_("Sets the gainXP permission for a PermRole.", True),
    )
    @has_guild_permissions(manage_guild=True)
    @commands.guild_only()
    async def pr_gain_xp(
        self,
        ctx: "MyContext",
        group: converters.PermGroup,
        role: converters.PermRole(-1),
        gain_xp: converters.OrNone(converters.mybool),
    ):
        await self.bot.db.permroles.edit(
            role.obj.id, group["id"], gain_xp=gain_xp
        )
        await ctx.send(
            embed=utils.cs_embed(
                {"gainXP": (role.sql["gain_xp"], gain_xp)}, self.bot
            )
        )

    @permroles.command(
        name="posRoles",
        aliases=["pr"],
        help=t_("Sets the posRoles permission for a PermRole.", True),
    )
    @has_guild_permissions(manage_guild=True)
    @commands.guild_only()
    async def pr_pos_roles(
        self,
        ctx: "MyContext",
        group: converters.PermGroup,
        role: converters.PermRole(-1),
        pos_roles: converters.OrNone(converters.mybool),
    ):
        await self.bot.db.permroles.edit(
            role.obj.id, group["id"], pos_roles=pos_roles
        )
        await ctx.send(
            embed=utils.cs_embed(
                {"posRoles": (role.sql["pos_roles"], pos_roles)}, self.bot
            )
        )

    @permroles.command(
        name="xpRoles",
        aliases=["xpr"],
        help=t_("Sets the xpRoles permission for a PermRole.", True),
    )
    @has_guild_permissions(manage_guild=True)
    @commands.guild_only()
    async def pr_xp_roles(
        self,
        ctx: "MyContext",
        group: converters.PermGroup,
        role: converters.PermRole(-1),
        xp_roles: converters.OrNone(converters.mybool),
    ):
        await self.bot.db.permroles.edit(
            role.obj.id, group["id"], xp_roles=xp_roles
        )
        await ctx.send(
            embed=utils.cs_embed(
                {"xpRoles": (role.sql["xp_roles"], xp_roles)}, self.bot
            )
        )


def setup(bot: "Bot"):
    bot.add_cog(PermRoles(bot))
