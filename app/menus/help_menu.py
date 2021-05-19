from typing import TYPE_CHECKING, List

import discord
from pretty_help import PrettyMenu

from .paginator import Paginator

if TYPE_CHECKING:
    from app.classes.context import MyContext


class HelpMenu(PrettyMenu):
    @staticmethod
    async def send_pages(
        ctx: "MyContext",
        destination: discord.abc.Messageable,
        embeds: List[discord.Embed],
    ):
        p = Paginator(embeds=embeds, delete_after=True)
        await p.start(ctx, channel=destination)
