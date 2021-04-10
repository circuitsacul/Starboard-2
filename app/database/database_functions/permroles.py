import typing

if typing.TYPE_CHECKING:
    from app.database.database import Database


class PermRoles:
    def __init__(self, db: Database):
        self.db = db
