from typing import TYPE_CHECKING

import discord
from discord.ext import commands, menus

import config

if TYPE_CHECKING:
    from app.classes.bot import Bot
    from app.classes.context import MyContext


class Menu(menus.Menu):
    def __init__(self, delete_after: bool = False, timeout: float = 180.0):
        super().__init__(
            delete_message_after=delete_after,
            clear_reactions_after=not delete_after,
            timeout=timeout,
        )

        if TYPE_CHECKING:
            self.bot: "Bot" = self.bot

    async def start(self, ctx, *, channel=None, wait=False):
        self.channel = channel
        self.wait = wait
        return await super().start(ctx, channel=channel, wait=wait)

    def reaction_check(self, payload):
        if payload.message_id != self.message.id:
            return False
        if payload.user_id not in {self._author_id, *config.OWNER_IDS}:
            return False
        return payload.emoji in self.buttons

    @staticmethod
    def _get_missing(permissions: discord.Permissions) -> list[str]:
        missing: list[str] = []
        if not permissions.read_messages:
            missing.append("View Channel")
        if not permissions.read_message_history:
            missing.append("Read Message History")
        if not permissions.add_reactions:
            missing.append("Add Reactions")
        if not permissions.embed_links:
            missing.append("Embed Links")
        return missing

    def _verify_permissions(
        self,
        ctx: "MyContext",
        channel: discord.abc.Messageable,
        permissions: discord.Permissions,
    ):
        missing = self._get_missing(permissions)
        if missing:
            raise commands.BotMissingPermissions(missing)

    async def on_menu_button_error(self, exc: Exception):
        self.stop()
        self.bot.dispatch("command_error", self.ctx, exc)
