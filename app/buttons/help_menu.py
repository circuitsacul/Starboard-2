from typing import TYPE_CHECKING, List

import discord
from discord.ext.prettyhelp import PrettyMenu

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
        pag = Paginator(
            ctx,
            embed_pages=embeds,
            delete_after=True,
        )
        await pag.start()
