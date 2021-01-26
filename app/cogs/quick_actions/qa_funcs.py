from typing import Optional


def get_qa_type(emoji: str, guild: dict) -> Optional[str]:
    qa_type: Optional[str] = None
    to_check = [
        "qa_force",
        "qa_unforce",
        "qa_freeze",
        "qa_trash",
        "qa_recount",
        "qa_save",
    ]
    for qat in to_check:
        if emoji == guild[qat]:
            qa_type = qat
            break
    return qa_type
