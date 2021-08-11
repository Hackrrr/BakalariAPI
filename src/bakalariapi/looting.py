"""Modul obsahující `Looting`, `ResultSet` a `GetterOutput`."""
from __future__ import annotations

import json
import logging
from threading import Lock
from typing import Generic, Type, TypeVar, cast

from bs4 import BeautifulSoup

from . import objects, utils
from .bakalari import BakalariAPI
from .objects import BakalariObj

# Ukázalo se, že importované TypeVar(y), odkazované přes namespace, nefungují tak jak by měli
# Když se nad tím člověk zamyslí, tak ono to dává asi i smysl, vzhledem k tomu, že i několik dalších věcí
# tak divně (ne)funguje při odkazování přes namespace (resp. nechovají se tak, jak by člověk mohl čekat)
# TypeVar odněkud importovaný a odkazovaný přes namespace se vždy bere jako nový typ. Např.:
#    def nejaka_funkce(x: objects.BakalariObj, y: objects.BakalariObj)
# Tato funkce dle hinteru bere 2 nějaké typy, které splňují objects.BakalariObj specifikaci.
# To ale není pravděpodobně to co je zde zamýšleno. Pravděpodobně autor chtěl říct, že oba argumenty
# mají mít stejný typ... Ale hinter tohle chápe jinak a proto se musí importovat TypeVar "přímo".

# Pozn. od mého budoucího já: Well... očividně se tady dějí ještě nějaké jiné divné další věci,
# a já nejsem schopný pochopit, co přesně... Hinter TypeVar importovaný "přímo" nějak nedokáže zpracovat
# a nedokáže správně "castit" a nevidí souvislosti. :)
# TL;DR - Hodil jsem tam 'cast' funkci, víc se s tím štvát nechci eShrug

__all__ = [
    "Looting",
    "ResultSet",
    "GetterOutput",
]

LOGGER = logging.getLogger("bakalariapi.looting")

GetterOutputTypeVar = TypeVar("GetterOutputTypeVar", BeautifulSoup, dict)


class GetterOutput(Generic[GetterOutputTypeVar]):
    """Třída používaná jako spojka mezi gettery a parsery."""

    def __init__(self, endpoint: str, data: GetterOutputTypeVar):
        self.endpoint: str = endpoint
        self.data: GetterOutputTypeVar = data
        self.type: Type[GetterOutputTypeVar] = type(data)


class ResultSet:
    """Třída používaná jako "lightweight looting"."""

    def __init__(
        self, loot: objects.BakalariObject | list[objects.BakalariObject] = None
    ):
        self.data: dict[str, list[objects.BakalariObject]] = {}
        if loot is not None:
            self.add_loot(loot)

    def add_loot(
        self, loot: objects.BakalariObject | list[objects.BakalariObject]
    ) -> ResultSet:
        """Přidá loot.

        Args:
            loot:
                Loot, který bude přidán.
        """
        if not isinstance(loot, list):
            loot = [loot]
        for o in loot:
            self.data.setdefault(type(o).__name__, []).append(o)
        return self

    def get(self, type_: Type[BakalariObj]) -> list[BakalariObj]:
        """Vrátí list objektů daného typu.

        Args:
            type_:
                Typ objektů, který se má vrátit.

        Returns:
            List objektů.
        """
        t = type_.__name__
        if t in self.data:
            return cast(list[BakalariObj], self.data[t])
        return []
        # return self.data[t] if t in self.data else []

    def merge(self, result_set: ResultSet) -> ResultSet:
        """Přidá loot z ResultSetu.

        Args:
            result_set:
                `ResultSet`, ze kterého bude přidán loot.
                `ResultSet` zůstane stejný.

        Returns:
            Navrátí se tato instance.
        """
        for (t, lst) in result_set.data.items():
            self.data[t] = self.data.setdefault(t, []) + lst
        return self

    def remove(self, type_: Type[objects.BakalariObject]) -> ResultSet:
        """Odstraní z lootu daný typ objektů.

        Args:
            type_:
                Typ objektů, který se má odstranit.

        Returns:
            Navrátí se tato instance.
        """
        try:
            del self.data[type_.__name__]
        except KeyError:
            pass
        return self


class Looting:
    """Třída obsatarávající sesbírané objekty pro pozdější použití.

    Pro získání dat z Looting instance je zde metoda `.get()`.

    Atributy:
        data:
            Slovník mají jako klíč název typu (string) a jako hodnotu slovík ID-Objekt.
            Klíče ve "vnořených" slovnících jsou také (vždy) string.
        unresolved:
            Slovník mají jako klíč název typu (string) a jako hodnotu slovík ID-UnresolvedID.
            Klíče ve "vnořených" slovnících jsou také (vždy) string.
    """

    def __init__(self):
        self.__lock = Lock()
        self.data: dict[str, dict[str, objects.BakalariObject]] = {}
        self.unresolved: dict[str, dict[str, objects.UnresolvedID]] = {}
        # Proč máme "root" key jako 'str' a ne jako 'type'? V runtimu asi lepší to mít jako 'type', ale při serializaci
        # nechci řešit nemožnost serializovat typ 'type' a při deserializaci nechci konvertovat něco (= typ, jako který
        # se to serializuje) zpátky na 'type'. Navíc I guess, že když __name__ je atribut, tak to prakticky nezabere nic.
        # Pozn. z budoucnosti: Ta myšlenka nekonverotování stringu na typ je pěkná, ale nějak se to nepodařilo dodržet KEKW

    def __add_one(self, o: objects.BakalariObject):
        """Přidá do lootu daný objekt."""
        if isinstance(o, objects.UnresolvedID):
            self.unresolved.setdefault(o.type.__name__, {})[o.ID] = o
        else:
            if (
                type(o).__name__ in self.unresolved
                and o.ID in self.unresolved[type(o).__name__]
            ):
                del self.unresolved[type(o).__name__][o.ID]
            self.data.setdefault(type(o).__name__, {})[o.ID] = o

    def add_loot(self, loot: objects.BakalariObject | list[objects.BakalariObject]):
        """Přidá loot.

        Args:
            loot:
                Loot, který bude přidán.
        """
        if not isinstance(loot, list):
            loot = [loot]
        self.__lock.acquire()
        try:
            for o in loot:
                self.__add_one(o)
        finally:
            self.__lock.release()

    def add_result_set(self, result_set: ResultSet):
        """Přidá loot z ResultSetu.

        Args:
            result_set:
                `ResultSet`, ze kterého bude přidán loot.
                `ResultSet` zůstane stejný.
        """
        self.__lock.acquire()
        try:
            for lst in result_set.data.values():
                # Jsem myslel, že to bude o trochu víc komplexnejší (jako třeba přeskočení resolvování typů) ale dopadlo to takhle KEKW
                for o in lst:
                    self.__add_one(o)
        finally:
            self.__lock.release()

    def get(self, type_: Type[BakalariObj]) -> list[BakalariObj]:
        """Vrátí list objektů daného typu.

        Args:
            type_:
                Typ objektů, který se má vrátit.

        Returns:
            List objektů.
        """
        if type_ == objects.UnresolvedID:
            return cast(
                list[BakalariObj], list(self.unresolved[type_.__name__].values())
            )
        try:
            return cast(
                list[BakalariObj],
                list(self.data.setdefault(type_.__name__, {}).values()),
            )
        except AttributeError:
            return []

    def resolve_unresolved(self, bakalariAPI: BakalariAPI):
        """Pokusí "vyřešit" všechny `UnresolvedID`.

        Args:
            bakalariAPI:
                Instance bakalariAPI, přes kterou se mají `UnresolvedID` "vyřešit".
        """
        unresolved = []
        for dct in self.unresolved.values():
            for v in dct.values():
                unresolved.append(v)
        self.add_result_set(bakalariAPI._resolve(unresolved))

    def export_json(self, *args, **kwargs):
        """Exportuje jako JSON data."""
        return json.dumps(
            {
                "data": self.data,
                "unresolved": self.unresolved,
            },
            cls=utils.JSONSerializer,
            *args,
            **kwargs,
        )

    def import_json(self, json_string: str, *args, **kwargs):
        """Importuje JSON data.

        Upozornění: Importovaní dat ze zdrojů, kterým nedůvěřujete, může být nebezpečné.
        Ačkoli je snaha o co největší bezpečnost, existuje zde bezpečnostní riziko.
        """
        parsed = json.loads(json_string, cls=utils.JSONDeserializer, *args, **kwargs)
        self.data = parsed["data"]
        self.unresolved = parsed["unresolved"]
