import os
import re
from typing import Optional

from dotenv import load_dotenv

from app.classes.bot import Bot

load_dotenv()

TOKEN = os.getenv("TENOR_KEY")

TENOR_PATTERN = re.compile(
    r"http[s]?:\/\/tenor.com\/view\/[a-zA-Z-]+(?P<id>\d+)"
)


def get_gif_id(url: str) -> Optional[int]:
    result = TENOR_PATTERN.match(url)
    if result:
        return result.groupdict()["id"]
    return None


async def get_gif_url(bot: Bot, url: str) -> Optional[str]:
    gifid = get_gif_id(url)
    if not gifid:
        return None

    try:
        async with bot.session.get(
            f"https://api.tenor.com/v1/gifs?ids={gifid}&key={TOKEN}", timeout=3
        ) as resp:
            resp.raise_for_status()
            data = await resp.json()
    except Exception:
        return None

    try:
        return data["results"][0]["media"][0]["gif"]["url"]
    except KeyError:
        return None
