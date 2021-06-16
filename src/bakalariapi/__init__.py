"""BakalářiAPI (resp. scraper) (nejen) pro domácí použití.

Modul primárně exportuje:
BakalariAPI - Základní classa pro práci s BakalářiAPI
LAST_SUPPORTED_VERSION - Konstanta definující nejnovější verzi Bakalářů, pro které byl tento modul testován
SeleniumHandler - Classa obsahující nastavení Selenia
Browser - Enum pro SeleniumHandler
"""


from . import bakalari, exceptions, looting, modules, seleniumhandler, sessions
from .bakalari import LAST_SUPPORTED_VERSION, BakalariAPI, GetMode
from .objects import *
from .seleniumhandler import Browser, SeleniumHandler

__all__ = [
    "BakalariAPI",
    "Looting",
    "LAST_SUPPORTED_VERSION",
    "SeleniumHandler",
    "Browser",
    "GetMode",
]
