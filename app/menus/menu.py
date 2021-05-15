from discord.ext import menus

import config


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
