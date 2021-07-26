"""Jednoduché (i složitější) utility sloužící ke správnému fungování BakalářiAPI."""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timedelta
from typing import Any, Protocol, TypeVar, cast, runtime_checkable

from bs4 import Tag
from requests.cookies import RequestsCookieJar
from selenium.webdriver.remote.webdriver import WebDriver

LOGGER = logging.getLogger("bakalariapi.utils")
LOGGER_SERIALIZER = logging.getLogger("bakalariapi.utils.serializer")


T0 = TypeVar("T0")
T1 = TypeVar("T1")
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
        # Ok, tady má `replace_with()` špatně stub a správně má brát i string
        br.replace_with("\n" + cast(Tag, br).text)

    body = soup.find("body")
    if body is not None:
        soup = cast(Tag, body)

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


@runtime_checkable
class Serializable(Protocol[T0, T1]):
    """Protokol, který implementují třídy, které jsou schopné serializace."""

    def serialize(self: T1) -> T0:
        """Serializuje objekt tak, aby ho mohla následně metoda `.deserialize()` deserializovat."""
        raise NotImplementedError()

    @classmethod
    def deserialize(cls, data: T0) -> T1:
        """Deserializuje data, které vyprodukovala `.serialize()` metoda."""
        raise NotImplementedError()


def resolve_string(string: str) -> Any:
    """Převede 'název' na objekt."""
    splitted = string.split(".")
    if splitted[0] not in sys.modules:
        try:
            __import__(splitted[0])
        except ModuleNotFoundError:
            return None
    pointer = sys.modules[splitted[0]]
    for part in splitted[1:]:
        # hasattr() check, ale lepší, takže neděláme 2x getattr() (hasattr() dělá getattr() interně)
        try:
            pointer = getattr(pointer, part)
        except AttributeError:
            return None
    return pointer


def get_full_type_name(t: type) -> str:
    """Vrátí celý název typu."""
    return f"{t.__module__}.{t.__name__}"


# TODO: Merge?
class JSONSerializer(json.JSONEncoder):
    def default(self, o):
        full_type_name = get_full_type_name(type(o))
        LOGGER_SERIALIZER.debug(
            "Serializing object %s resolved to type %s", o, full_type_name
        )
        if isinstance(o, datetime):
            LOGGER_SERIALIZER.debug(
                "... special handling (object seems like datetime instance)"
            )
            return {
                "_type": full_type_name,
                "data": o.isoformat(),
            }
        if isinstance(o, Serializable):
            LOGGER_SERIALIZER.debug(
                "... special handling (object implemets Serializable protocol)"
            )
            return {"_type": full_type_name, "data": o.serialize()}
        return super().default(o)


class JSONDeserializer(json.JSONDecoder):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, object_hook=self.hook, **kwargs)

    def hook(self, o):
        LOGGER_SERIALIZER.debug("Deserializing object %s", o)
        if "_type" not in o:
            return o
        real_type = resolve_string(o["_type"])
        LOGGER_SERIALIZER.debug('... found "_type" value, resolved to %s', real_type)
        if real_type == datetime:
            LOGGER_SERIALIZER.debug("... deserializing via special case")
            return datetime.fromisoformat(o["data"])
        if issubclass(real_type, Serializable):
            LOGGER_SERIALIZER.debug(
                "... resolved type has implementation of Serializable protocol, deserializing via this protocol"
            )
            return real_type.deserialize(o["data"])
        raise TypeError("Unknown type to load; Type: " + o["_type"])


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
