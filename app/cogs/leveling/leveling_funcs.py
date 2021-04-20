def current_level(xp: int) -> int:
    if xp <= 0:
        return 0
    return int((xp / 10) ** 0.3) + 1
