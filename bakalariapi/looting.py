from __future__ import annotations

import json
from datetime import datetime
from typing import Type
from multiprocessing import Lock

from .bakalari import ResultSet, BakalariAPI
from . import bakalariobjects, utils

__all__ = [
    "Looting",
]

class Looting:
    """Třída obsatarávající sesbírané objekty pro pozdější použití.

    Pro získání dat z Looting instance je zde metoda `.get()`

    Atributy:
        data:
            Slovník mají jako klíč název typu (string) a jako hodnotu slovík ID-Objekt.
            Klíče ve "vnořených" slovnících jsou také (vždy) string.
        unresolved:
            Slovník mají jako klíč název typu (string) a jako hodnotu slovík ID-UnresolvedID.
            Klíče ve "vnořených" slovnících jsou také (vždy) string.
    """
    class JSONEncoder(json.JSONEncoder):
        def default(self, o):
            full_type_name = utils.get_full_type_name(type(o))
            #print(f"Serializing {full_type_name}: {o}")
            if isinstance(o, datetime):
                return {
                    "_type": full_type_name,
                    "data": o.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
                }
            if isinstance(o, utils.Serializable):
                return {
                    "_type": full_type_name,
                    "data": o.serialize()
                } 
            return super().default(o)
    class JSONDecoder(json.JSONDecoder):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, object_hook=self.hook, **kwargs)
        def hook(self, o):
            if "_type" not in o:
                return o
            real_type = utils.resolve_string(o["_type"])
            if real_type == datetime:
                return datetime.strptime(o["data"], "%Y-%m-%dT%H:%M:%S.%fZ")
            if issubclass(real_type, utils.Serializable):
                return real_type.deserialize(o["data"])
            raise TypeError("Unknown type to load; Type: " + o["_type"])

    def __init__(self):
        self.__lock = Lock()
        self.data: dict[str, dict[str, bakalariobjects.BakalariObject]] = {}
        self.unresolved: dict[str, dict[str, bakalariobjects.UnresolvedID]] = {}
        # Proč máme "root" key jako 'str' a ne jako 'type'? V runtimu asi lepší to mít jako 'type', ale při serializaci
        # nechci řešit nemožnost serializovat typ 'type' a při deserializaci nechci konvertovat něco (= typ, jako který
        # se to serializuje) zpátky na 'type'. Navíc I guess, že když __name__ je atribut, tak to prakticky nezabere nic.
        # Pozn. z budoucnosti: Ta myšlenka nekonverotování stringu na typ je pěkná, ale nějak se to nepodařilo dodržet KEKW

    def __add_one(self, o: bakalariobjects.BakalariObject):
        if isinstance(o, bakalariobjects.UnresolvedID):
            self.unresolved.setdefault(o.type.__name__, {})[o.ID] = o
        else:
            if type(o).__name__ in self.unresolved and o.ID in self.unresolved[type(o).__name__]:
                del self.unresolved[type(o).__name__][o.ID]
            self.data.setdefault(type(o).__name__, {})[o.ID] = o

    def add_loot(self, loot: bakalariobjects.BakalariObject | list[bakalariobjects.BakalariObject]):
        if not isinstance(loot, list):
            loot = [loot]
        self.__lock.acquire()
        try:
            for o in loot:
                self.__add_one(o)
        finally:
            self.__lock.release()
    def add_result_set(self, result_set: ResultSet):
        self.__lock.acquire()
        try:
            for lst in result_set.data.values():
                for o in lst:
                    self.__add_one(o)
                # Jsem myslel, že to bude o trochu víc komplexnejší (jako třeba přeskočení resolvování typů) ale dopadlo to takhle KEKW
        finally:
            self.__lock.release()

    def get(self, type_: Type[bakalariobjects.BakalariObj]) -> list[bakalariobjects.BakalariObj]:
        if type_ == bakalariobjects.UnresolvedID:
            return list(self.unresolved[type_.__name__].values())
        return list(self.data[type_.__name__].values())

    def resolve_unresolved(self, bakalariAPI: BakalariAPI):
        unresolved = []
        for dct in self.unresolved.values():
            for v in dct.values():
                unresolved.append(v)
        self.add_result_set(bakalariAPI._resolve(unresolved)) #pylint: disable=protected-access


    def export_JSON(self, *args, **kwargs):
        return json.dumps({
            "data": self.data,
            "unresolved": self.unresolved,
        }, cls=self.JSONEncoder, *args, **kwargs)

    def import_JSON(self, json_string: str, *args, **kwargs):
        parsed = json.loads(json_string, cls=self.JSONDecoder, *args, **kwargs)
        self.data = parsed["data"]
        self.unresolved = parsed["unresolved"]
