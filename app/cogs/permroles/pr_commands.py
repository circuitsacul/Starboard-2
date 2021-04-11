import typing
from typing import Optional

import discord
from discord.ext import commands

from app import converters, menus, utils
from app.i18n import t_

if typing.TYPE_CHECKING:
    from app.classes.bot import Bot


class PermRoles(commands.Cog):
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
        await self.bot.db.permgroups.delete(group["id"])
        await ctx.send(t_("Deleted PermGroup {0}").format(group["name"]))

    @permgroups.command(name="move", brief="Sets the position of a permgroup")
    @commands.has_guild_permissions(manage_guild=True)
    @commands.guild_only()
    async def move_permgroup(
        self, ctx: commands.Context, group: converters.PermGroup, position: int
    ):
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


def setup(bot: "Bot"):
    bot.add_cog(PermRoles(bot))
