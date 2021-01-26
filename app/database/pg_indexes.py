MEMBERS__USER_ID = """CREATE INDEX IF NOT EXISTS
    members__user_id ON members (user_id)"""

ALL_INDEXES = [MEMBERS__USER_ID]
