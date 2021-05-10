import contextvars
import gettext
import os.path
import typing
from glob import glob

import discord

import config
from app.classes.t_string import TString

if typing.TYPE_CHECKING:
    from app.classes.bot import Bot

BASE_DIR = "app/"
LOCALE_DEFAULT = "en_US"
LOCALE_DIR = "locale"
locales = frozenset(
    map(
        os.path.basename,
        filter(os.path.isdir, glob(os.path.join(BASE_DIR, LOCALE_DIR, "*"))),
    )
)

gettext_translations = {
    locale: gettext.translation(
        "bot",
        languages=(locale,),
        localedir=os.path.join(BASE_DIR, LOCALE_DIR),
    )
    for locale in locales
}

gettext_translations["en_US"] = gettext.NullTranslations()
locales |= {"en_US"}


def use_current_gettext(*args, **kwargs) -> str:
    if not gettext_translations:
        return gettext.gettext(*args, **kwargs)

    locale = current_locale.get()
    return gettext_translations.get(
        locale, gettext_translations[LOCALE_DEFAULT]
    ).gettext(*args, **kwargs)


def t_(string: str, as_obj: bool = False) -> TString:
    tstring = TString(string, use_current_gettext)
    if as_obj:
        return tstring
    return str(tstring)  # translate immediatly


current_locale: contextvars.ContextVar = contextvars.ContextVar("i18n")


def set_current_locale():
    current_locale.set(LOCALE_DEFAULT)


def language_embed(bot: "Bot", p: str) -> discord.Embed:
    return discord.Embed(
        title="Languages",
        color=bot.theme_color,
        description=t_(
            "You can now choose your personal and server language. "
            "Use `{p}guildLang <language>` to set the language for "
            "the server (applies to starboard messages, level up "
            "messages, etc.), or `{p}lang <language>` to set your "
            "personal language.\n\n"
            "Valid Languages:\n{languages}"
        ).format(
            p=p,
            languages=" - "
            + "\n - ".join([lang["name"] for lang in config.LANGUAGE_MAP]),
        ),
    )


set_current_locale()
