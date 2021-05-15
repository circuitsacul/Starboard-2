from typing import TYPE_CHECKING, Optional

import discord
from discord.ext import menus

from .menu import Menu

if TYPE_CHECKING:
    from app.classes.context import MyContext


class Paginator(Menu):
    def __init__(
        self,
        embeds: Optional[list[discord.Embed]] = None,
        text: Optional[list[str]] = None,
        delete_after: bool = False,
    ) -> None:
        super().__init__(delete_after=delete_after)
        self.embeds = embeds
        self.text = text
        self.current_page = 0
        self.length = len(embeds) if embeds else len(text)

        if self.embeds and self.length != 1:
            for x, e in enumerate(self.embeds):
                to_add = f"({x+1}/{self.length})"
                footer = (
                    e.footer.text + "\n" + to_add
                    if isinstance(e.footer.text, str)
                    else to_add
                )
                e.set_footer(text=footer, icon_url=e.footer.icon_url)
        if self.length == 1:
            self.remove_button(self.skip_to_first.__menu_button__)
            self.remove_button(self.skip_to_last.__menu_button__)
            self.remove_button(self.next.__menu_button__)
            self.remove_button(self.back.__menu_button__)
            if not delete_after:
                self.remove_button(self.stop_menu.__menu_button__)

    async def start(self, ctx, *, channel=None, wait=False):
        if self.length == 1 and not self.delete_message_after:
            return await self.send_initial_message(ctx, channel or ctx.channel)
        return await super().start(ctx, channel=channel, wait=wait)

    async def send_initial_message(
        self, ctx: "MyContext", channel: discord.TextChannel
    ) -> discord.Message:
        return await ctx.send(
            self.text[self.current_page] if self.text else None,
            embed=self.embeds[self.current_page] if self.embeds else None,
        )

    async def edit_page(self, increment: int) -> None:
        self.current_page += increment

        if self.current_page < 0:
            self.current_page = self.length - 1
        elif self.current_page > self.length - 1:
            self.current_page = 0

        embed = self.embeds[self.current_page] if self.embeds else None
        text = self.text[self.current_page] if self.text else None

        try:
            await self.message.edit(content=text, embed=embed)
        except discord.NotFound:
            self.stop()

    @menus.button("\N{BLACK LEFT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}")
    async def skip_to_first(
        self, payload: discord.RawReactionActionEvent
    ) -> None:
        self.current_page = 0
        await self.edit_page(0)

    @menus.button("\N{BLACK LEFT-POINTING TRIANGLE}")
    async def back(self, payload: discord.RawReactionActionEvent) -> None:
        await self.edit_page(-1)

    @menus.button("\N{BLACK RIGHT-POINTING TRIANGLE}")
    async def next(self, payload: discord.RawReactionActionEvent) -> None:
        await self.edit_page(1)

    @menus.button("\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}")
    async def skip_to_last(
        self, payload: discord.RawReactionActionEvent
    ) -> None:
        self.current_page = self.length - 1
        await self.edit_page(0)

    @menus.button("\N{BLACK SQUARE FOR STOP}")
    async def stop_menu(self, payload: discord.RawReactionActionEvent) -> None:
        self.stop()
