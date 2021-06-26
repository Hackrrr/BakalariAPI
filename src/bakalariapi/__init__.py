"""BakalářiAPI (resp. scraper) (nejen) pro domácí použití.

Modul primárně exportuje:
BakalariAPI - Základní classa pro práci s BakalářiAPI
GetMode - Enum sloužící pro specifikování módu při získávání dat
Looting - Třída pro správu získaných dat
LAST_SUPPORTED_VERSION - Konstanta definující nejnovější verzi Bakalářů, pro které byl tento modul testován
SeleniumHandler - Classa obsahující nastavení Selenia
Browser - Enum pro SeleniumHandler
"""


from . import bakalari, exceptions, looting, modules, seleniumhandler, sessions, objects
from .bakalari import LAST_SUPPORTED_VERSION, BakalariAPI, GetMode
from .objects import (
    ServerInfo,
    UserInfo,
    BakalariObject,
    UnresolvedID,
    BakalariFile,
    KomensFile,
    HomeworkFile,
    Komens,
    Grade,
    MeetingProvider,
    Meeting,
    Student,
    Homework,
)
from .seleniumhandler import Browser, SeleniumHandler

__all__ = [
    "BakalariAPI",
    "GetMode",
    "Looting",
    "LAST_SUPPORTED_VERSION",
    "SeleniumHandler",
    "Browser",
    # From .objects:
    "ServerInfo",
    "UserInfo",
    "BakalariObject",
    "UnresolvedID",
    "BakalariFile",
    "KomensFile",
    "HomeworkFile",
    "Komens",
    "Grade",
    "MeetingProvider",
    "Meeting",
    "Student",
    "Homework",
]
