from typing import Optional

import discord
from discord.ext import commands, menus
from pretty_help import PrettyMenu


class HelpMenu(PrettyMenu):
    @staticmethod
    async def send_pages(
        ctx: commands.Context,
        destination: discord.abc.Messageable,
        embeds: list[discord.Embed],
    ):
        p = Paginator(embeds=embeds, delete_after=True)
        await p.start(ctx, channel=destination)


class Confirm(menus.Menu):
    def __init__(self, message: str) -> None:
        super().__init__(timeout=30, delete_message_after=True)
        self.msg = message
        self.result = None

    async def send_initial_message(
        self, ctx: commands.Context, channel: discord.TextChannel
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

    async def start(self, ctx: commands.Context) -> Optional[bool]:
        await super().start(ctx, wait=True)
        return self.result


class Paginator(menus.Menu):
    def __init__(
        self,
        embeds: Optional[list[discord.Embed]] = None,
        text: Optional[list[str]] = None,
        delete_after: bool = False,
    ) -> None:
        super().__init__(
            clear_reactions_after=not delete_after,
            delete_message_after=delete_after,
        )
        self.embeds = embeds
        self.text = text
        self.current_page = 0
        self.length = len(embeds) if embeds else len(text)

        if self.embeds:
            for x, e in enumerate(self.embeds):
                to_add = f"({x+1}/{self.length})"
                footer = (
                    e.footer.text + "\n" + to_add
                    if isinstance(e.footer.text, str)
                    else to_add
                )
                e.set_footer(text=footer, icon_url=e.footer.icon_url)

    @classmethod
    async def help_menu(
        cls: "Paginator",
        ctx: commands.Context,
        destination: discord.abc.Messageable,
        pages: list[discord.Embed],
    ):
        paginator = cls(pages, delete_after=True)
        await paginator.start(ctx, channel=destination)

    async def send_initial_message(
        self, ctx: commands.Context, channel: discord.TextChannel
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
