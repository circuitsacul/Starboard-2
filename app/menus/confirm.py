import typing
from typing import Optional

import discord
from discord.ext import menus

from .menu import Menu

if typing.TYPE_CHECKING:
    from app.classes.context import MyContext


class Confirm(Menu):
    def __init__(self, message: str) -> None:
        super().__init__(timeout=30, delete_after=True)
        self.msg = message
        self.result = None

    async def send_initial_message(
        self, ctx: "MyContext", channel: discord.TextChannel
    ) -> discord.Message:
        return await ctx.send(self.msg)

    @menus.button("\N{WHITE HEAVY CHECK MARK}")
    async def confirm(self, payload: discord.RawReactionActionEvent) -> None:
        self.result = True
        self.stop()

    @menus.button("\N{CROSS MARK}")
    async def deny(self, payload: discord.RawReactionActionEvent) -> None:
        self.result = False
        self.stop()

    async def start(
        self, ctx: "MyContext", channel=None, wait=True
    ) -> Optional[bool]:
        await super().start(ctx, wait=wait)
        return self.result
