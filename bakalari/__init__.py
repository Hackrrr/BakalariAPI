"""BakalářiAPI (resp. scraper) (nejen) pro domácí použití.

Modul primárně exportuje:
BakalariAPI - Základní classa pro práci s BakalářiAPI
Looting - Classa starající se o perzistenci (ukládání a načítání) výsledků
LAST_SUPPORTED_VERSION - Konstanta definující poslední verzi Bakalářů, pro které byl tento modul testován
SeleniumHandler - Classa obsahující nastavení Selenia
Browser - Enum pro SeleniumHandler
exceptions - Vyjímky, které mohou nastat za běhu BakalářiAPI.
"""


from . import exceptions
from .bakalari import *
from .bakalariobjects import *
#from .modules import *

__all__ = ["BakalariAPI", "LAST_SUPPORTED_VERSION", "Looting", "SeleniumHandler", "Browser", "exceptions"]
#No need to expose classes from bakalariobjects as they shouldn't be created "by hand" (resp. from anywhere else but BakalariAPI)
