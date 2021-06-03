from typing import TYPE_CHECKING, List, Optional, Tuple

import discord
from discord_components.button import ButtonStyle
from discord_components.context import Context as Interaction
from discord_components.interaction import InteractionType

from app.i18n.i18n import t_

from .buttons import Button, ButtonMenu, MenuButton, button

if TYPE_CHECKING:
    from app.classes.context import MyContext


class Paginator(ButtonMenu):
    def __init__(
        self,
        ctx: "MyContext",
        *,
        text_pages: List[str] = None,
        embed_pages: List[discord.Embed] = None,
        delete_after: bool = False,
    ):
        if not (text_pages or embed_pages):
            raise RuntimeError("You must pass something to paginate.")

        self.text_pages = text_pages
        self.embed_pages = embed_pages
        self.current_page = 0

        super().__init__(
            ctx.bot,
            ctx.channel,
            ctx.author.id,
            timeout=180.0,
            remove_after=not delete_after,
        )

        self.grouped_buttons[0].insert(
            2,
            MenuButton(
                Button(label=self.page_num_text, disabled=True),
                lambda ctx: None,
                remove=False,
            ),
        )

    async def start(self):
        await super().start()
        if not self.remove_after:
            try:
                await self.message.delete()
            except discord.NotFound:
                pass

    @property
    def page_num_text(self):
        return t_("Page {0}/{1}").format(self.current_page + 1, self.length)

    @property
    def length(self):
        return max(
            len(self.text_pages) if self.text_pages else 0,
            len(self.embed_pages) if self.embed_pages else 0,
        )

    def page(self, num: int) -> Tuple[Optional[str], Optional[discord.Embed]]:
        return (
            self.text_pages[num] if self.text_pages else None,
            self.embed_pages[num] if self.embed_pages else None,
        )

    async def send_initial_message(self) -> discord.Message:
        text, embed = self.page(self.current_page)
        return await self.destination.send(
            text, embed=embed, components=self.buttons_list
        )

    async def update_page(self):
        text, embed = self.page(self.current_page)
        await self.message.edit(
            text, embed=embed, components=self.buttons_list
        )

    async def increment_page(self, value: int):
        self.current_page += value
        if self.current_page >= self.length:
            self.current_page = 0
        elif self.current_page < 0:
            self.current_page = self.length - 1

        self.grouped_buttons[0][2].button._label = self.page_num_text

        await self.update_page()

    @button(Button(label=t_("Stop", True), style=ButtonStyle.red), pos=0)
    async def stop_pag(self, ctx: Interaction):
        await ctx.respond(type=InteractionType.DeferredUpdateMessage)
        self.running = False

    @button(Button(label=t_("Prev", True), style=ButtonStyle.blue), pos=1)
    async def prev_page(self, ctx: Interaction):
        await ctx.respond(type=InteractionType.DeferredUpdateMessage)
        await self.increment_page(-1)

    @button(Button(label=t_("Next", True), style=ButtonStyle.blue), pos=2)
    async def next_page(self, ctx: Interaction):
        await ctx.respond(type=InteractionType.DeferredUpdateMessage)
        await self.increment_page(1)
