from typing import Optional


def get_qa_type(emoji: str, guild: dict) -> Optional[str]:
    if emoji == guild["qa_force"]:
        return "qa_force"
    elif emoji == guild["qa_unforce"]:
        return "qa_unforce"
    elif emoji == guild["qa_freeze"]:
        return "qa_freeze"
    elif emoji == guild["qa_trash"]:
        return "qa_trash"
    elif emoji == guild["qa_recount"]:
        return "qa_recount"
    elif emoji == guild["qa_save"]:
        return "qa_save"
    else:
        return None
