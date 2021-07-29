import os
import re
from typing import Optional, Tuple

from dotenv import load_dotenv

from app.classes.bot import Bot

load_dotenv()

TENOR_TOKEN = os.getenv("TENOR_KEY")
GIPHY_TOKEN = os.getenv("GIPHY_KEY")

TENOR_BASE = "https://api.tenor.com/v1/gifs?ids={0}&key={1}"
GIPHY_BASE = "https://api.giphy.com/v1/gifs/{0}"

TENOR_PATTERN = re.compile(
    r"^http[s]?:\/\/tenor.com\/view\/[a-zA-Z-]+(?P<id>\d+)$"
)
GIPHY_PATTERN = re.compile(
    r"^http[s]?:\/\/giphy.com\/gifs\/[a-zA-Z-]+-(?P<id>[\w]+)$"
)


def _get_gif_id(url: str) -> Optional[Tuple[str, str]]:
    """Gets the id of a gif as well as the service it was from
    based on a url.

    :param url: The url of the possible gif
    :type url: str
    :return: The gif id and the service, or None if not found
    :rtype: Optional[Tuple[str, str]]
    """
    tenor_result = TENOR_PATTERN.match(url)
    if tenor_result:
        return tenor_result.groupdict()["id"], "tenor"
    giphy_result = GIPHY_PATTERN.match(url)
    if giphy_result:
        return giphy_result.groupdict()["id"], "giphy"
    return None


async def _get(bot: Bot, url: str, *args, **kwargs) -> dict:
    """Call bot.session.get, resp.raise_for_status, and then return
    the resulting json.

    :param bot: The bot instance
    :type bot: Bot
    :param url: The url to get from
    :type url: str
    :return: The json that was returned
    :rtype: dict
    """
    async with (await bot.session()).get(
        url, *args, timeout=3, **kwargs
    ) as resp:
        resp.raise_for_status()
        data = await resp.json()
    return data


async def _get_tenor(bot: Bot, gifid: str) -> Optional[str]:
    """Get the media url of a gif from tenor's api.

    :param bot: The bot instance
    :type bot: Bot
    :param gifid: The id of the gif
    :type gifid: str
    :return: The media url, or None if not found
    :rtype: Optional[str]
    """
    if not TENOR_TOKEN:
        return None

    try:
        data = await _get(bot, TENOR_BASE.format(gifid, TENOR_TOKEN))
        return data["results"][0]["media"][0]["gif"]["url"]
    except Exception:
        return None


async def _get_giphy(bot: Bot, gifid: str) -> Optional[str]:
    """Get the media url of a gif from giphy's api.

    :param bot: The bot instance
    :type bot: Bot
    :param gifid: The id of the gif
    :type gifid: str
    :return: The media url, or None if not found
    :rtype: Optional[str]
    """
    if not GIPHY_TOKEN:
        return None

    try:
        params = {"api_key": GIPHY_TOKEN}
        data = await _get(bot, GIPHY_BASE.format(gifid), params=params)
        return data["data"]["images"]["fixed_height"]["url"]
    except Exception:
        return None


async def get_gif_url(bot: Bot, url: str) -> Optional[str]:
    """Get the media url of either a tenor or giphy gif, or None
    if it's not a gif.

    :param bot: The bot instance
    :type bot: Bot
    :param url: The url of the possible gif
    :type url: str
    :return: The media url, or None if not a gif
    :rtype: Optional[str]
    """
    result = _get_gif_id(url)
    if not result:
        return None

    gifid, service = result

    if service == "tenor":
        return await _get_tenor(bot, gifid)
    elif service == "giphy":
        return await _get_giphy(bot, gifid)
