from math import sqrt


def next_level_xp(current_level: int) -> int:
    return int((current_level + 1) ** 2)


def current_level(xp: int) -> int:
    if xp < 0:
        return 0
    return int(sqrt(xp))
