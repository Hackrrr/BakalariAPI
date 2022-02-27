"""Jednoduché (i složitější) utility sloužící ke správnému fungování BakalářiAPI."""

from __future__ import annotations

import logging
import sys
import warnings
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, Generic, TypeVar, Union, cast, get_args, overload

# Pojďme si zodpovědět ozázku, proč je tu tohle?
# Núže... Bylo nebylo, pyright zase zklamal. Teda ne že bych se divil,
# vzhledem k tomu, že je to kvůli `_CustomChecks` (meta)třídě, která
# rozhodně porušuje celý zen Pythonu. Problém má základ v importu
# `_ProtocolMeta` z `typing` modulu - jak pyright, tak i mypy, si při
# něm stěžujou na to, že `_ProtocolMeta` neexistuje. Ok, přeci jen to
# absolutně nikdo nemá používat, takže tohle beru. Bohužel to má ale
# za následek, že se typ `_ProtocolMeta` jeví jako `Unknown` pro
# pyright a jako `Any` pro mypy. A to je očividně problém, pokud toho
# začneme derivovat a použijeme derivovaný typ jako metatřídu (tak jak
# to s `_CustomChecks` děláme).
# Nikdo si na nic nestěžuje, ale je tu takový "malý" zádrhel, který
# se ukáže, když se pokusíme něco typovat pomocí třídy, která má
# takovoutu "divnou" metatřídu. Mypy si s tím poradí v pohodě, pyright
# bohužel už ne. Přepodkládejme toto:
#   class MyMeta(Any): ...
#   class A(metaclass=MyMeta): ...
#   def test(value: A | list[A]): reveal_type(value)
# Mypy správně vyhodí, že typ pro `value` je `A | list[A]`, ale
# pyright vyhodí, že `value` je typu `Unknown`. A abychom tento
# problém vyřešili, tak třída `_ProtocolMeta` musí být někde "správně"
# definovaná a to je ten důvod, proč je tady tento `if`.
# Pozn.: Docela zvláštní je to, že pyright správně ukáže typ, pokud
# daný typ nemá v sobě 2x `A` (v tomto případě). Tzn., že třeba `A`
# nebo `list[A] | None` projde v pořádku.
if TYPE_CHECKING:
    # fmt: off
    from abc import ABCMeta
    class _ProtocolMeta(ABCMeta): ... 
    # fmt: on
else:
    from typing import _ProtocolMeta

from bs4 import BeautifulSoup, MarkupResemblesLocatorWarning
from bs4.element import Tag  # Kvůli mypy - https://github.com/python/mypy/issues/10826
from requests.cookies import RequestsCookieJar
from selenium.webdriver.remote.webdriver import WebDriver
from typing_extensions import TypeGuard

LOGGER = logging.getLogger("bakalariapi.utils")


T0 = TypeVar("T0")
T0_co = TypeVar("T0_co", covariant=True)
T1 = TypeVar("T1")
T1_co = TypeVar("T1_co", covariant=True)
T2 = TypeVar("T2")


def first2upper(string: str) -> str:
    """První znak ve stringu dá do Uppercase."""
    return string[0].upper() + string[1:]


def string2datetime(string: str) -> datetime:
    """Pokusí se získat převést string na datum dle předdefinovaných formátů. Pokud neuspěje, vyhodí ValueError."""
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S%z",
        "%Y-%m-%d %H:%M:%ST%z",
        "%Y-%m-%d",
    ]
    for date_format in formats:
        try:
            return datetime.strptime(string, date_format)
        except ValueError:
            pass
    raise ValueError


def line_iterator(text: str):
    """Slouží jako iterátor řádek pro text. (Vypůjčeno (resp. ukradeno) ze Stacku.)"""
    prevnl = -1
    while True:
        nextnl = text.find("\n", prevnl + 1)
        if nextnl < 0:
            break
        yield text[prevnl + 1 : nextnl]
        prevnl = nextnl


def parseHTML(markup: str | bytes) -> BeautifulSoup:
    with warnings.catch_warnings():
        # viz docstring warningu
        warnings.simplefilter("ignore", MarkupResemblesLocatorWarning)
        return BeautifulSoup(markup, "html.parser")


def bs_get_text(soup: Tag) -> str:
    """BeautifulSoup.get_text(), ale tak trochu jinak
    BeautifulSoup dělá vynikající práci... Ale na prasárny Bakalářů to ani tak nestačí
    To co tohle udělá a '.get_text()' ne:
        - Nahradí "<br/>" za \n... '.get_text()' zvládá jen syntakticky správně (tedy "<br />" nebo jen "<br>")
        - Pokud je zde "<body>" tag, tak vezme jen ten
        - Stripne text (Je to vůbec potřeba? eShrug)
    """

    # TODO: Převést <p> na nové řádky
    for br in soup("br"):
        br = cast(Tag, br)
        br.replace_with("\n" + br.text)

    body = cast(Tag, soup.find("body"))
    if body is not None:
        soup = body

    return soup.get_text().strip()


def cs_timedelta(
    time: timedelta, order: str, skip_zero: bool = True, placeholder: str = "okamžik"
) -> str:
    """Vrátí timedeltu slovně v češtině.

    Args:
        time:
            Časový rozdíl, který se má převést
        order:
            Formát výstupu / Pořadí, ve kterém se jednotlivé části zapíší, např. "dhm".
            Možné části:
                d - Dny
                h - Hodiny
                m - Minuty
                s - Sekundy
                f - Mikrosekundy
            Není nutné, aby se všechny části vykytli, avšak jejich hodnota bude ztracena.
            (tzn. že pokud např. se zde "m" (minuty) nebude přítomno a "s" (sekundy) ano, tak se minuty na sekundy NEpřevedou)
            Jednotlivé části se mohou opakovat vícekrát.
        skip_zero:
            Pokud True, tak se přeskočí výpis hodnoty (resp. dané části), pokud je rovna nule.
            Pokud False, hodnota (resp. část) se napíše i přestože je rovna nule.
        placeholder:
            Pokud by výsledný string měl nulovou délku, tak se výstup nahradí tímto stringem.
    Returns:
        Český slovní popis vstupní timedelty.

    Raises:
        ValueError: Neplatný žádaný formát v "order" argumentu
    """
    output = []

    microseconds = time.microseconds % 1000
    # milisecods = (time.microseconds - microseconds) / 1000
    seconds = time.seconds % 60
    minutes = int(((time.seconds - seconds) / 60) % 60)
    hours = int((time.seconds - seconds - minutes * 60) / 3600)
    days = time.days

    # Jasně, určitě šlo by tohle šlo udělat nějak pěkněji (např. mít tyto data třeba ve slovníku), ale pro jednou bych se držel KISS pravidla :)
    for char in order:
        if char == "d":
            tmp = abs(days)
            if skip_zero and tmp == 0:
                continue
            if tmp == 1:
                output.append(f"{days} den")
            elif tmp <= 4 and tmp != 0:
                output.append(f"{days} dny")
            else:
                output.append(f"{days} dnů")
        elif char == "h":
            tmp = abs(hours)
            if skip_zero and tmp == 0:
                continue
            if tmp == 1:
                output.append(f"{hours} hodina")
            elif tmp <= 4 and tmp != 0:
                output.append(f"{hours} hodiny")
            else:
                output.append(f"{hours} hodin")
        elif char == "m":
            tmp = abs(minutes)
            if skip_zero and tmp == 0:
                continue
            if tmp == 1:
                output.append(f"{minutes} minuta")
            elif tmp <= 4 and tmp != 0:
                output.append(f"{minutes} minuty")
            else:
                output.append(f"{minutes} minut")
        elif char == "s":
            tmp = abs(seconds)
            if skip_zero and tmp == 0:
                continue
            if tmp == 1:
                output.append(f"{seconds} sekunda")
            elif tmp <= 4 and tmp != 0:
                output.append(f"{seconds} sekundy")
            else:
                output.append(f"{seconds} sekund")
        elif char == "f":
            tmp = abs(microseconds)
            if skip_zero and tmp == 0:
                continue
            if tmp == 1:
                output.append(f"{microseconds} mikrosekunda")
            elif tmp <= 4 and tmp != 0:
                output.append(f"{microseconds} mikrosekundy")
            else:
                output.append(f"{microseconds} mikrosekund")
        else:
            raise ValueError("Invalid order format")

    return human_join(output) if len(output) > 0 else placeholder


def human_join(lst: list, connector: str = ", ", last_connector: str = " a ") -> str:
    """Lidsky spojí list a vrátí výsledek jako string."""
    l = len(lst)
    if l == 0:
        return ""
    if l == 1:
        return str(lst[0])
    return connector.join(lst[:-1]) + last_connector + lst[-1]


def line_modifier(text: str, prefix: str = "", suffix: str = "") -> str:
    """Modifikuje string řádku po řádce."""
    lines = [f"{prefix}{line}{suffix}" for line in line_iterator(text)]
    return "\n".join(lines)


def resolve_string(string: str, reverse: bool = False) -> Any:
    """Převede "název" na objekt. V případě nenalezení vrátí `None`.

    Prakticky reverzní operace `get_full_type_name()`.

    V určitých případech může funkce vracet něco jiného, než předpokládáte.
    Vezměme následující (reálný) příklad:
    Modul `bakalarishell` má submodul/package `main`, ale naneštěstí definuje i funkci `main`.
    `resolve_string("bakalarishell.main")` by v tomto případě vrátila funkci `main`.
    Proto tento případ existuje "primitivní" parametr `reverse`, který "hledá od zadu", resp.
    pokusí se importovat co nejnižší (sub)modul a až poté začne brát v potaz ostatní atributy.
    """
    pointer = None
    split: list[str]

    if reverse:
        split = []
        index = len(string)
        while True:
            try:
                # Python je zase divný... A protože v tomhle souboru zřejmě potkáme úplně všechny
                # nesmyslnosti, které Python má, tak jsme zase v psaní komentáře :)
                # `__import__` z nějakého důvodu vrací (v základu) jen top-level modul. Tzn. při
                # pokusu o import "bakalariapi.objects" by vrátil modul "bakalariapi", nikoliv
                # (chtěný) submodul. Abychom dostali submodul, musíme mít "non-empty" parametr
                # `fromlist`, který, dle dokumentace, absulutně nic nedělá (doslova nic). Jeho
                # jediný účel je buď být prázdný (default) nebo neprázdný (a umožnit tak import
                # submodulu).
                pointer = __import__(string[:index], fromlist=[""])
            except ModuleNotFoundError:
                index = string.rfind(".", 0, index)
                if index == -1:
                    return None
                continue
            if index == len(string):
                return pointer
            else:
                split = [string[:index], string[index + 1 :]]
                break
    else:
        split = string.split(".")
        try:
            pointer = __import__(split[0])
        except ModuleNotFoundError:
            return None

    for part in split[1:]:
        # hasattr() check, ale lepší, takže neděláme 2x getattr() (hasattr() dělá getattr() interně)
        try:
            pointer = getattr(pointer, part)
        except AttributeError:
            return None
    return pointer


def get_full_type_name(t: type) -> str:
    """Vrátí celý název typu."""
    return f"{t.__module__}.{t.__name__}"


def cookies_webdriver2requests(webdriver: WebDriver) -> dict[str, str]:
    """Převede Selenium cookies do formátu cookies pro `requests` modul."""
    return {entry["name"]: entry["value"] for entry in webdriver.get_cookies()}


def cookies_requests2webdriver(cookies: RequestsCookieJar) -> list[dict[str, Any]]:
    """Převede `RequestsCookieJar` do formátu cookies pro Selenium."""
    return [
        {
            "name": cookie.name,
            "value": cookie.value,
            "path": cookie.path,
            "domain": cookie.domain,
            "secure": cookie.secure,
            # "expiry": cookie.expires # Protože nevím, jak si selenium poradí s případnou hodnotou None
        }
        for cookie in cookies
    ]


def is_typed_dict(data_dict: Any, typed_dict: type[T0]) -> TypeGuard[T0]:
    # Měl by tu být i paramter "type_check: bool", ale jelikož `typing` modul nemá žádnou
    # metodu, která by ověřila správnost typu, tak by bylo potřeba napsat vlastní typechecker
    # a to není tak jednoduché, jak by se mohlo zdát LULW. Ano, zkusil jsem to, ale existuje
    # extrémní množství "krajních případů" (resp. jen "případů"), které se musí odchytit.
    # Nakonec jsem ale usoudil, že za tu práci to (zatím) nestojí.
    # Nejsnadnější věc by byla vzít tenhle script: https://stackoverflow.com/a/55504010
    # nebo použít tohle: https://github.com/agronholm/typeguard; https://stackoverflow.com/a/65735336
    if not isinstance(data_dict, dict):
        return False
    if len(data_dict) != len(typed_dict.__annotations__):
        return False
    for name, type_ in typed_dict.__annotations__.items():
        if name not in data_dict:
            return False
        # if type_check and not check_type(data_dict[name], type_):
        #     return False
    return True


def is_union(obj, union: type[T0]) -> TypeGuard[T0]:
    return isinstance(obj, get_args(union))


# Vítejte u další epizody "Hackujeme Python, protože opět potřebujeme
# udělat něco, co nikdo nepřepodkládal, že by někdo mohl chtít dělat...".
# Dnes nás čeká hraní si s metatřídami... Ano, to je ta věc v Pythonu,
# na kterou se opravdu nemá šahat. "Pokud nevíš, jestli potřebuješ
# metatřídy, tak je nepotřebuješ". Naneštěstí my je tentokrát potřebujeme,
# jelikož v chceme, aby si jednotlivé třídy mohli definovat vlastní
# `__instancecheck__()` a `__subclasscheck__()`, který z nějakého zvláštního
# důvodu lze definovat pouze na metatřídě (IDK, tak je to v dokumentaci).
#
# Nejdříve umožníme implementaci `__instancecheck__()` a `__subclasscheck__()`
# ze tříd, které budou mít tuto třídu jako metatřídu. To uděláme tak, že
# v "našich" `__instancecheck__()` a `__subclasscheck__()` definicích
# zkontrolujeme, zda daná třída implementuje danou metodu - pokud ano, použijeme
# tu, pokud ne, necháme to na originální implementaci (tzn. implementace z
# `type` (meta)třídy).
# Krok číslo jedna hotov. Problém je, že pokud použijeme u naší třídy
# `_CustomChecks` jako base třídu `type`, tak pokud následně nějaká třída
# bude chtít použít `_CustomChecks` jako metatřídu a zároveň bude derivovat
# ze třídy, která bude používat jako metatřídu něco jiného, tak je problém,
# jelikož `_CustomChecks` nebude subtřída všech metatříd v definici třídy,
# což vyustí v `TypeError`. Srozumitelněji:
#   class MetaA(type): ...
#   class MetaB(type): ...
#   class A(metaclass=MetaA): ...
#   class B(metaclass=MetaB): ...
#   class D(A, B): ...
# Definice `D` bude mít za následek `TypeError`, protože defaulntní metatřída
# `type` není subtřídou `MetaA` a `MetaB` (alespoň tak to chápu já). Řešení?
# Vytvořit novou třídu, která derivuje ze všech metatříd, které použivají
# třídy, ze kterých chceme derivovat. Tzn.:
#   class MetaA(type): ...
#   class MetaB(type): ...
#   class A(metaclass=MetaA): ...
#   class B(metaclass=MetaB): ...
#   class MetaAB(MetaA, MetaB): ...
#   class D(A, B, metaclass=MetaAB): ...
# Ale co když máme X tříd, které pokaždé derivují z jiných tříd, které mají
# vlastní metatřídy? Tak ano, muselo by se vytvořit X metatříd, které derivují
# z daných (meta)tříd. A nebo udělat nějaký hack jako je tohle:
#   https://stackoverflow.com/questions/4651729/metaclass-mixin-or-chaining
# Proč to teda nepoužiji? Jelikož je to věc z roku 2011, tak je to Python 2.x
# a upgradovat se mi to nechce. Takže co s tím? Nic. eShrug Tenhle problém je
# nevyřešený. Jediné, co můžeme udělat je derivovat nejčastější metatřídě, co
# se bude potkávat a to jest `abc.ABCMeta`, což mimochodem i udělá z naší třídy
# abstraktní třídu, takže takový bonus navíc.
# That's all folks! To byl dnešní díl vašeho oblíbeného seriálu rozbíjení
# v Pythonu a budeme se na vás těštit v další epizodě.
# Pozn.: Tady používám `_ProtocolMeta`, jelikož to je metatřída pro `Protocol`,
# tudíž lze použít `_CustomChecks` jako metatřídu, když se derivuje
# z `Protocol`. `_ProtocolMeta` derivuje z `abc.ABCMeta`, takže `_CustomChecks`
# zůstává stále jako abstraktní třída.


class _CustomChecks(_ProtocolMeta):
    """Použití:
    ```
    class MojeTrida(metaclass=_CustomChecks):
        @classmethod
        def __instancecheck__(self, instance: Any) -> bool:
            ...
    ```
    """

    def __instancecheck__(self, instance: Any) -> bool:
        if issubclass(type(type(self)), _CustomChecks) and hasattr(
            type(self), "__instancecheck__"
        ):
            return type(self).__instancecheck__(instance)  # type: ignore # "__instancecheck__" neexsituje :)
        return type.__instancecheck__(self, instance)

    def __subclasscheck__(self, subclass: type) -> bool:
        if issubclass(type(self), _CustomChecks) and hasattr(self, "__subclasscheck__"):
            return self.__subclasscheck__(subclass)  # type: ignore # "__subclasscheck__" neexsituje :)
        return type.__subclasscheck__(self, subclass)


# Už dlouho jsme nic nerozbíleji, je čas to změnit.
# Dnes máme na programu dne slovník, jehož záznamy by se daly anotovat jako:
#   Klíč: T0
#   Hodnota: list[T0]
# Tudíž např. pokud přítoupíme ke klíči `int`, dostaneme `list[int]`.
# Bohužel tohoto nelze docílit skrze současný systém typování v Pythonu.
# Řešení je jednoduché, že? Jen vytvoříme sub-type slovníku/`dict`.
# Samozřejmě, že ne :) Problémy objevily hned po zkoušce užití. Budeme
# muset tedy zase trochu hackovat Python (resp. typování v Pythonu).
# Spoiler alert: Nepůjde to; Alespoň ne 100% správně :(
# Problém je, že chceme mít slovník daného typu. Tzn., že T0 chceme mít bounded
# k typu, který specifikujeme při anotaci (`ListDict[Base]`). Problém je,
# že nyní nemůžeme napsat `__getitem__(self, k: type[T0]) -> list[T0]`.
# Proč? Protože by jsme vlastně napsali `(k: type[Base]) -> list[Base]`, což
# ale není to co chceme. Špatně to vlastně není, ale my chceme mít typ listu
# více specifikovaný (na typ, který je v parametru).
# A celý tento problém je, že nemůžeme udělat typevar bounded typevarem. Nyní
# totiž musíme napsat `(k: type[T1]) -> list[T1]` (musíme použít jiný typever),
# ale tento jiný typevar nemá žádnou spojitost s originálním, takže můžeme
# napsat `d: ListDict[Base]; reveal_type(d[int])` a type checker vše povolí
# (a vyhodí typ `int`), protože nikdo neomezil typevar T1. Řešení neexistuje.
# Je možné, že řešení půjde udělat skrze kovariatní return type (typevaru T0),
# ale IDK, jestli to bude povolený až se (jestli vůbec) povede přijmout PEP
# poskytující nový syntax pro kontra-/ko- varianci:
#   https://github.com/python/typing/issues/813
#   https://github.com/python/peps/pull/2045
#
# Další problém je, že ne všechny věci lze v takovémto slovníku udělat.
# Např. class metoda `.fromkeys()`. To jest dáno tím, že jsem neudělal nic :).
# Jediné, co jsem provedl, je úprava type anotací metod a runtime implementace
# je buď `NotImplementedError` nebo `super()`. Z toho také plyne následek, že
# runtime se tento (nový) slovník chová prakticky stejně a je možné ho jednoduše
# invalidovat - zde se spoléhá na ochranu přes statické type checkery. Poslední
# věc je inicializace. Nelze inicializovat dosazením `{}`. Ničemu to neškodí,
# ale docela mě štve, že to udělat nelze.

# BTW tohle je vzácný případ deaktivace formátování - jelikož se jedná prakticky
# jedná pouze o type anotace, které se ovšem nenacházejí v ".pyi", black je bere
# jako normální funkce a tak je také formátuje. Naneštěstí takovéto formátování
# vypadá v tomto případě otřesně (např. `...` na novém řádku).
# fmt: off
class ListDict(dict[type[T0], list[T0]], Generic[T0]):
    # T1 by měl mít T0 jako upper bound, ale to v Pythonu napsat nejde
    def __init__(self):
        """
        """
        pass
        
    @classmethod
    def fromkeys(cls, __iterable, __value): raise NotImplementedError()

    @overload
    def get(self, __key: type[T1]) -> Union[list[T1], None]: ...
    @overload
    def get(self, __key: type[T1], __default: Union[list[T1], T2]) -> Union[list[T1], T2]: ...
    def get(self, *args, **kwargs) -> Any: return super().get(*args, **kwargs)

    @overload
    def pop(self, __key: type[T1]) -> list[T1]: ...
    @overload
    def pop(self, __key: type[T1], __default: Union[list[T1], T2] = ...) -> Union[list[T1], T2]: ...
    def pop(self, *args, **kwargs) -> Any: return super().pop(*args, **kwargs)

    def __getitem__(self, __k: type[T1]) -> list[T1]: return super().__getitem__(__k) #type: ignore
    def __setitem__(self, __k: type[T1], v: list[T1]) -> None: return super().__setitem__(__k, v) #type: ignore

    if sys.version_info >= (3, 9):
        def __class_getitem__(cls, __item): raise NotImplementedError()
        def __or__(self, __value): raise NotImplementedError()
        def __ror__(self, __value): raise NotImplementedError()
        def __ior__(self, __value): raise NotImplementedError()
# fmt: on
