from collections import OrderedDict
from copy import deepcopy
from typing import Awaitable, Callable, Optional

import discord
from discord.ext import commands, menus
from pretty_help import PrettyMenu

import config

ZERO_WIDTH_SPACE = "\u200B"


class HelpMenu(PrettyMenu):
    @staticmethod
    async def send_pages(
        ctx: commands.Context,
        destination: discord.abc.Messageable,
        embeds: list[discord.Embed],
    ):
        p = Paginator(embeds=embeds, delete_after=True)
        await p.start(ctx, channel=destination)


class Menu(menus.Menu):
    def __init__(self, delete_after: bool = False, timeout: float = 180.0):
        super().__init__(
            delete_message_after=delete_after,
            clear_reactions_after=not delete_after,
            timeout=timeout,
        )

    def reaction_check(self, payload):
        if payload.message_id != self.message.id:
            return False
        if payload.user_id not in {self._author_id, *config.OWNER_IDS}:
            return False
        return payload.emoji in self.buttons


class Confirm(Menu):
    def __init__(self, message: str) -> None:
        super().__init__(timeout=30, delete_after=True)
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


class _AccordionField:
    def __init__(self, accordion: "Accordion", name: str, value: str):
        self.name = name
        self.value = value
        self._accordion = accordion
        self.embed: Optional[discord.Embed] = None

    async def _set_to(self):
        if not self.embed:
            embed: discord.Embed = deepcopy(self._accordion._embed)
            embed.clear_fields()
            for field in self._accordion.fields:
                if field is self:
                    value = self.value
                else:
                    value = ZERO_WIDTH_SPACE
                embed.add_field(name=field.name, value=value, inline=False)
            self.embed = embed

        await self._accordion.message.edit(embed=self.embed)


NUMBER_EMOJIS = [
    "1️⃣",
    "2️⃣",
    "3️⃣",
    "4️⃣",
    "5️⃣",
    "6️⃣",
    "7️⃣",
    "8️⃣",
    "9️⃣",
    "🔟",
]


class Accordion(Menu):
    def __init__(self, embed: discord.Embed):
        super().__init__(delete_after=True)
        self._embed = embed
        self._embed.clear_fields()
        self.fields: list["_AccordionField"] = []

        self._buttons = OrderedDict()

    async def start(self, ctx, *, channel=None, wait=False):
        self.set_buttons()
        return await super().start(ctx, channel=channel, wait=wait)

    async def send_initial_message(
        self, ctx: commands.Context, destination: discord.abc.Messageable
    ):
        for field in self.fields:
            self._embed.add_field(
                name=field.name, value=ZERO_WIDTH_SPACE, inline=False
            )
        return await destination.send(embed=self._embed)

    @staticmethod
    def _set_field(
        field: "_AccordionField",
    ) -> Callable[
        ["Accordion", discord.RawReactionActionEvent], Awaitable[None]
    ]:
        async def set_field(
            menu: "Accordion", payload: discord.RawReactionActionEvent
        ):
            await field._set_to()

        return set_field

    def set_buttons(self):
        for num, field in enumerate(self.fields):
            emoji = NUMBER_EMOJIS[num]
            field.name = f"{emoji} {field.name}"
            self._buttons[emoji] = menus.Button(
                emoji,
                self._set_field(field),
            )
        self._buttons["\N{BLACK SQUARE FOR STOP}"] = menus.Button(
            "\N{BLACK SQUARE FOR STOP}", self.astop
        )

    async def astop(self, payload):
        return self.stop()

    def add_field(self, name: str, value: str) -> "Accordion":
        self.fields.append(_AccordionField(self, name, value))
        return self
