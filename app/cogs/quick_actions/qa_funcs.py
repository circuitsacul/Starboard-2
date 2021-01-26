from typing import Optional


def get_qa_type(emoji: str, guild: dict) -> Optional[str]:
    qa_type: Optional[str] = None
    if emoji == guild["qa_force"]:
        qa_type = "qa_force"
    elif emoji == guild["qa_unforce"]:
        qa_type = "qa_unforce"
    elif emoji == guild["qa_freeze"]:
        qa_type = "qa_freeze"
    elif emoji == guild["qa_trash"]:
        qa_type = "qa_trash"
    elif emoji == guild["qa_recount"]:
        qa_type = "qa_recount"
    elif emoji == guild["qa_save"]:
        qa_type = "qa_save"
    return qa_type
