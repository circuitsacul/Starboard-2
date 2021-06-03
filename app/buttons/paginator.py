from typing import TYPE_CHECKING, List, Optional, Tuple

import discord
from discord_components.button import Button, ButtonStyle
from discord_components.context import Context as Interaction
from discord_components.interaction import InteractionType

from .buttons import ButtonMenu, MenuButton, button

if TYPE_CHECKING:
    from app.classes.context import MyContext


class Paginator(ButtonMenu):
    def __init__(
        self,
        ctx: "MyContext",
        *,
        text_pages: List[str] = [],
        embed_pages: List[discord.Embed] = [],
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
            1,
            MenuButton(
                Button(label=f"Page 1/{self.length}", disabled=True),
                lambda ctx: None,
                remove=False,
            ),
        )

    async def start(self):
        await super().start()
        if not self.remove_after:
            await self.message.delete()

    @property
    def length(self):
        return max(len(self.text_pages), len(self.embed_pages))

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

        self.grouped_buttons[0][
            1
        ].button.label = f"Page {self.current_page + 1}/{self.length}"

        await self.update_page()

    @button(Button(label="Prev", style=ButtonStyle.blue), pos=0)
    async def prev_page(self, ctx: Interaction):
        await ctx.respond(type=InteractionType.DeferredUpdateMessage)
        await self.increment_page(-1)

    @button(Button(label="Next", style=ButtonStyle.blue), pos=1)
    async def next_page(self, ctx: Interaction):
        await ctx.respond(type=InteractionType.DeferredUpdateMessage)
        await self.increment_page(1)
