import typing
from typing import Optional

import discord
from discord.ext import commands

from app import converters, errors, menus, utils
from app.i18n import t_

from . import pr_functions

if typing.TYPE_CHECKING:
    from app.classes.bot import Bot


class PermRoles(commands.Cog):
    """Manage PermRoles for a server"""

    def __init__(self, bot: "Bot"):
        self.bot = bot

    @commands.group(
        name="permgroups",
        aliases=["pg", "permroles", "pr"],
        brief="Lists permgroups, or views settings for a permgroup.",
        invoke_without_command=True,
    )
    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    async def permgroups(
        self,
        ctx: commands.Context,
        group: Optional[converters.PermGroup] = None,
    ):
        """Lists permgroups, or views settings for a specific permgroup."""
        if not group:
            groups = await self.bot.db.permgroups.get_many(ctx.guild.id)
            if not groups:
                await ctx.send(t_("You have no permgroups."))
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
            embed = (
                discord.Embed(
                    title=f"PermGroup {group['name']}",
                    color=self.bot.theme_color,
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

    @permgroups.command(name="add", brief="Add a permgroup")
    @commands.bot_has_permissions(embed_links=True)
    @commands.has_guild_permissions(manage_guild=True)
    @commands.guild_only()
    async def add_permgroup(self, ctx: commands.Context, name: str):
        """Adds a permgroup"""
        await self.bot.db.permgroups.create(ctx.guild.id, name)
        await ctx.send(t_("Created PermGroup {0}").format(name))

    @permgroups.command(
        name="delete",
        aliases=["remove", "rm", "del"],
        brief="Deletes a permgroup",
    )
    @commands.has_guild_permissions(manage_guild=True)
    @commands.guild_only()
    async def del_permgroup(
        self, ctx: commands.Context, group: converters.PermGroup
    ):
        """Deletes a permgroup"""
        await self.bot.db.permgroups.delete(group["id"])
        await ctx.send(t_("Deleted PermGroup {0}").format(group["name"]))

    @permgroups.command(name="move", brief="Sets the position of a permgroup")
    @commands.has_guild_permissions(manage_guild=True)
    @commands.guild_only()
    async def move_permgroup(
        self, ctx: commands.Context, group: converters.PermGroup, position: int
    ):
        """Changes the index of a permgroup.

        If these were your permgroups:
            1. Group1
            2. Group2
            3. Group3
        Running permgroups move Group1 3 would change it to:
            1. Group2
            2. Group3
            3. Group1"""
        new_index = await self.bot.db.permgroups.move(group["id"], position)
        await ctx.send(
            t_("Moved the PermGroup {0} from {1} to {2}.").format(
                group["name"], group["index"], new_index
            )
        )

    @permgroups.group(
        name="channels",
        aliases=["c"],
        brief="Manage the channels that a PermGroup affects",
        invoke_without_command=True,
    )
    @commands.has_guild_permissions(manage_guild=True)
    @commands.guild_only()
    async def pg_channels(self, ctx: commands.Context):
        """Manage the channels that a PermGroup affects"""
        await ctx.send_help(ctx.command)

    @pg_channels.command(
        name="add",
        aliases=["a"],
        brief="Adds channel(s) to the list of channels for a PermGroup",
    )
    @commands.has_guild_permissions(manage_guild=True)
    @commands.guild_only()
    async def add_pg_channels(
        self,
        ctx: commands.Context,
        group: converters.PermGroup,
        *channels: discord.TextChannel,
    ):
        """Adds one or more channels to the list of channels for a
        PermGroup"""
        current_channels = set(int(cid) for cid in group["channels"])
        for c in channels:
            current_channels.add(c.id)
        current_channels = list(current_channels)

        await self.bot.db.permgroups.set_channels(
            group["id"], current_channels
        )
        await ctx.send(
            t_("Added {0} to the channels on PermGroup {1}.").format(
                ", ".join(c.mention for c in channels), group["name"]
            )
        )

    @pg_channels.command(
        name="remove",
        aliases=["rm", "r", "del", "delete"],
        brief="Removes channel(s) from the list of channels on a PermGroup",
    )
    @commands.has_guild_permissions(manage_guild=True)
    @commands.guild_only()
    async def remove_pg_channels(
        self,
        ctx: commands.Context,
        group: converters.PermGroup,
        *channels: discord.TextChannel,
    ):
        """Removes one or more channels from the list of channels on a
        PermGroup"""
        current_channels = set(int(cid) for cid in group["channels"])
        for c in channels:
            current_channels.remove(c.id)
        current_channels = list(current_channels)

        await self.bot.db.permgroups.set_channels(
            group["id"], current_channels
        )
        await ctx.send(
            t_("Removed {0} from the channels on PermGroup {1}.").format(
                ", ".join(c.mention for c in channels), group["name"]
            )
        )

    @pg_channels.command(
        name="clear", brief="Clears all channels from a PermGroup"
    )
    @commands.has_guild_permissions(manage_guild=True)
    @commands.guild_only()
    async def clear_pg_channels(
        self, ctx: commands.Context, group: converters.PermGroup
    ):
        """Removes all channels from the list of channels
        on a PermGroup"""
        if not await menus.Confirm(
            t_(
                "Are you sure you want to clear all channels for "
                "the PermGroup {0}?"
            ).format(group["name"])
        ).start(ctx):
            await ctx.send(t_("Cancelled."))
            return

        await self.bot.db.permgroups.set_channels(group["id"], [])
        await ctx.send(
            t_("Cleared all channels for the PermGroup {0}.").format(
                group["name"]
            )
        )

    @permgroups.group(
        name="starboards",
        aliases=["s"],
        brief="Manage the starboards that a PermGroup affects",
        invoke_without_command=True,
    )
    @commands.has_guild_permissions(manage_guild=True)
    @commands.guild_only()
    async def pg_starboards(
        self,
        ctx: commands.Context,
    ):
        """Manage the starboards that a PermGroup affects"""
        await ctx.send_help(ctx.command)

    @pg_starboards.command(
        name="add",
        aliases=["a"],
        brief="Adds starboard(s) to the list of starboards for a PermGroup",
    )
    @commands.has_guild_permissions(manage_guild=True)
    @commands.guild_only()
    async def add_pg_starboards(
        self,
        ctx: commands.Context,
        group: converters.PermGroup,
        *starboards: converters.Starboard,
    ):
        """Adds one or more starboards to the list of starboards on a
        PermGroup"""
        current_starboards = set(int(sid) for sid in group["starboards"])
        for s in starboards:
            current_starboards.add(s.obj.id)
        current_starboards = list(current_starboards)
        await self.bot.db.permgroups.set_starboards(
            group["id"], current_starboards
        )
        await ctx.send(
            t_("Added {0} to the starboards on PermGroup {1}.").format(
                ", ".join(s.obj.mention for s in starboards), group["name"]
            )
        )

    @pg_starboards.command(
        name="remove",
        aliases=["r", "rm", "del", "delete"],
        brief="Removes starboard(s) from the list of starboars on a PermGroup",
    )
    @commands.has_guild_permissions(manage_guild=True)
    @commands.guild_only()
    async def remove_pg_starboards(
        self,
        ctx: commands.Context,
        group: converters.PermGroup,
        *starboards: converters.Starboard,
    ):
        """Removes one or more starboards from the list of starboards
        on a PermGroup"""
        current_starboards = set(int(sid) for sid in group["starboards"])
        for s in starboards:
            current_starboards.remove(s.obj.id)
        current_starboards = list(current_starboards)
        await self.bot.db.permgroups.set_starboards(
            group["id"], current_starboards
        )
        await ctx.send(
            t_("Removed {0} from the starboards on PermGroup {1}.").format(
                ", ".join(s.obj.mention for s in starboards), group["name"]
            )
        )

    @pg_starboards.command(
        name="clear", brief="Clears all starboards on a PermGroup"
    )
    @commands.has_guild_permissions(manage_guild=True)
    @commands.guild_only()
    async def clear_pg_starboards(
        self, ctx: commands.Context, group: converters.PermGroup
    ):
        """Removes all starboards from the list of starboards on a
        PermGroup"""
        if not await menus.Confirm(
            t_(
                "Are you sure you want to clear all starboards "
                "for the PermGroup {0}?"
            ).format(group["name"])
        ).start(ctx):
            await ctx.send("Cancelled.")
            return

        await self.bot.db.permgroups.set_starboards(group["id"], [])
        await ctx.send(
            t_("Cleared all starboards for PermGroup {0}.").format(
                group["name"]
            )
        )

    @permgroups.group(
        name="roles",
        aliases=["permroles", "pr"],
        brief="Manage/View PermRoles for a PermGroup",
        invoke_without_command=True,
    )
    @commands.has_guild_permissions(manage_guild=True)
    @commands.guild_only()
    async def permroles(
        self,
        ctx: commands.Context,
        group: converters.PermGroup,
    ):
        """Manage PermRoles for a PermGroup"""
        permroles = await self.bot.db.permroles.get_many(group["id"])
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
        name="add", aliases=["a"], brief="Adds a PermRole to a PermGroup"
    )
    @commands.has_guild_permissions(manage_guild=True)
    @commands.guild_only()
    async def add_permrole(
        self,
        ctx: commands.Context,
        group: converters.PermGroup,
        role: discord.Role,
    ):
        """Sets a role as a PermRole on a PermGroup"""
        if (await self.bot.db.permroles.get(role.id, group["id"])) is not None:
            raise errors.PermRoleAlreadyExists(role.name, group["name"])

        await self.bot.db.permroles.create(group["id"], role.id)
        await ctx.send(
            t_("{0} is now a PermRole on the PermGroup {1}.").format(
                role.name, group["name"]
            )
        )

    @permroles.command(
        name="remove",
        aliases=["r", "rm", "del", "delete"],
        brief="Removes a PermRole from a PermGroup",
    )
    @commands.has_guild_permissions(manage_guild=True)
    @commands.guild_only()
    async def remove_permrole(
        self,
        ctx: commands.Context,
        group: converters.PermGroup,
        role: discord.Role,
    ):
        """Removes a PermRole from a PermGroup"""
        permrole = await self.bot.db.permroles.get(role.id, group["id"])
        if not permrole:
            raise errors.PermRoleNotFound(role.name, group["name"])

        await self.bot.db.permroles.delete(role.id, group["id"])
        await ctx.send(
            t_("{0} is no longer a PermRole on the PermGroup {1}.").format(
                role, group["name"]
            )
        )

    @permroles.command(
        name="move", brief="Changes the position of a PermRole in a PermGroup"
    )
    @commands.has_guild_permissions(manage_guild=True)
    @commands.guild_only()
    async def move_permrole(
        self,
        ctx: commands.Context,
        group: converters.PermGroup,
        role: discord.Role,
        new_position: converters.myint,
    ):
        """Changes the index of a PermRole within a PermGroup"""
        permrole = await self.bot.db.permroles.get(role.id, group["id"])
        if not permrole:
            raise errors.PermRoleNotFound(role.name, group["name"])

        new_index = await self.bot.db.permroles.move(
            role.id, group["id"], new_position
        )
        await ctx.send(
            t_("Moved the PermRole {0} from {1} to {2}.").format(
                role.name, permrole["index"], new_index
            )
        )


def setup(bot: "Bot"):
    bot.add_cog(PermRoles(bot))
