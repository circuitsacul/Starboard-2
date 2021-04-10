import typing
from typing import Optional

import discord
from discord.ext import commands

from app import errors
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
        self, ctx: commands.Context, name: Optional[str] = None
    ):
        if not name:
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
            group = await self.bot.db.permgroups.get_name(ctx.guild.id, name)
            embed = discord.Embed(
                title=group["name"],
                color=self.bot.theme_color,
                description=str(group),
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
    async def del_permgroup(self, ctx: commands.Context, name: str):
        group = await self.bot.db.permgroups.get_name(ctx.guild.id, name)
        if not group:
            raise errors.PermGroupNotFound(name)
        await self.bot.db.permgroups.delete(group["id"])
        await ctx.send(t_("Deleted PermGroup {0}").format(group["name"]))

    @permgroups.command(name="move", brief="Sets the position of a permgroup")
    @commands.has_guild_permissions(manage_guild=True)
    @commands.guild_only()
    async def move_permgroup(
        self, ctx: commands.Context, name: str, position: int
    ):
        group = await self.bot.db.permgroups.get_name(ctx.guild.id, name)
        if not group:
            raise errors.PermGroupNotFound(name)
        new_index = await self.bot.db.permgroups.move(group["id"], position)
        await ctx.send(
            t_("Moved the PermGroup {0} from {1} to {2}.").format(
                group["name"], group["index"], new_index
            )
        )


def setup(bot: "Bot"):
    bot.add_cog(PermRoles(bot))
