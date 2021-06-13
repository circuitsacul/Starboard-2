class SpecialType:
    def __init__(self, name: str):
        """A class for generating custom types.

        :param name: The name of the constant/type
        :type name: str
        """
        self.name = name

    def __repr__(self):
        return self.name

    __str__ = __repr__


# Classes
MISSING = SpecialType("MISSING")

# Characters
ZWS = "\u200B"
ARROW_LEFT = "←"
ARROW_RIGHT = "→"

# Values
MAX_EMBED_DESC_LENGTH = 2_048
PREMIUM_MONTH_DAYS = 31

# Emoji Lists
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
