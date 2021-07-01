from typing import Awaitable, Callable, Optional, Tuple

import discord
from discord.ext import menus

from .menu import Menu


class Scroll(Menu):
    def __init__(
        self,
        page_getter: Callable[
            [int],
            Awaitable[Optional[Tuple[Optional[str], Optional[discord.Embed]]]],
        ],
        start: int = 0,
    ):
        self.current = start
        self.getter = page_getter

        super().__init__(True)

    async def send_initial_message(
        self, ctx, channel: discord.abc.Messageable
    ):
        text, embed = await self.getter(self.current)
        return await channel.send(text, embed=embed)

    async def update_page(self, new_page: int):
        result = await self.getter(new_page)
        if result:
            text, embed = result
            self.current = new_page
            await self.message.edit(content=text, embed=embed)

    def increment(self, value: int) -> int:
        new = self.current + value
        if new < 0:
            new = 0
        return new

    @menus.button("\N{BLACK LEFT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}")
    async def skip_to_first(
        self, payload: discord.RawReactionActionEvent
    ) -> None:
        await self.update_page(0)

    @menus.button("\N{BLACK LEFT-POINTING TRIANGLE}")
    async def back(self, payload: discord.RawReactionActionEvent) -> None:
        await self.update_page(self.increment(-1))

    @menus.button("\N{BLACK RIGHT-POINTING TRIANGLE}")
    async def next(self, payload: discord.RawReactionActionEvent) -> None:
        await self.update_page(self.increment(1))

    @menus.button("\N{BLACK SQUARE FOR STOP}")
    async def stop_menu(self, payload: discord.RawReactionActionEvent) -> None:
        self.stop()
