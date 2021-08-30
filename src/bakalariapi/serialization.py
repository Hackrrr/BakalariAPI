from __future__ import annotations

__all__ = [
    "register",
    "serialize",
    "deserialize",
    "SerializedData",
    "Serializable",
]

import copy
import logging
from datetime import datetime
from typing import (
    Any,
    Callable,
    Iterable,
    Literal,
    Mapping,
    Protocol,
    TypedDict,
    TypeVar,
    Union,
    cast,
    overload,
    runtime_checkable,
)

from . import exceptions
from .utils import T0, get_full_type_name, is_typed_dict, is_union, resolve_string

LOGGER = logging.getLogger("bakalariapi.serialization")

SerializablePrimitive = Union[
    bool,
    float,
    int,
    None,
    str,
]
SerializableValue = Union[
    SerializablePrimitive,
    Mapping[str, "SerializableValue"],  # type: ignore # Mypy nepodporuje rekurzi  https://github.com/python/mypy/issues/731
    Iterable["SerializableValue"],  # type: ignore # Mypy nepodporuje rekurzi  https://github.com/python/mypy/issues/731
]
RawSerializableValue = Union[
    SerializableValue,
    Mapping[str, Any],
    Iterable[Any],
]
TSerializablePrimitive = TypeVar("TSerializablePrimitive", bound=SerializablePrimitive)
TSerializableValue = TypeVar("TSerializableValue", bound=SerializableValue)
TRawSerializableValue = TypeVar("TRawSerializableValue", bound=RawSerializableValue)


class SerializedData(TypedDict):
    __type__: str
    data: SerializableValue


class RawSerializedData(TypedDict):
    __type__: str
    data: RawSerializableValue


_serializers: dict[
    type,
    tuple[
        Callable[[object], RawSerializableValue],
        Callable[[RawSerializableValue], object],
    ],
] = {}


def register(
    type_: type[T0],
    serializer: Callable[[T0], TRawSerializableValue],
    deserializer: Callable[[TRawSerializableValue], T0],
):
    _serializers[type_] = (serializer, deserializer)


@runtime_checkable
class Serializable(Protocol[TRawSerializableValue]):
    """Protokol, který implementují třídy, které jsou schopné serializace."""

    def serialize(self) -> TRawSerializableValue:
        """Serializuje objekt tak, aby ho mohla následně metoda `.deserialize()` deserializovat."""
        raise NotImplementedError()

    @classmethod
    def deserialize(cls: type[T0], data: TRawSerializableValue) -> T0:
        """Deserializuje data, které vyprodukovala `.serialize()` metoda."""
        raise NotImplementedError()


@overload
def serialize(obj: TSerializablePrimitive) -> TSerializablePrimitive:
    ...


@overload
def serialize(obj: RawSerializableValue, recursive: Literal[True]) -> SerializableValue:
    ...


@overload
def serialize(
    obj: TRawSerializableValue, recursive: Literal[False]
) -> TRawSerializableValue:
    ...


@overload
def serialize(obj: object, recursive: Literal[True]) -> SerializedData:
    ...


@overload
def serialize(obj: object, recursive: Literal[False]) -> RawSerializedData:
    ...


def serialize(
    obj: object, recursive: bool = True
) -> SerializableValue | SerializedData | RawSerializedData:
    # To že je `recusive` jako dobrovolný parametr je kvůli 1. overloadu

    if is_union(obj, SerializablePrimitive):
        # Pokud je primitive, necháme tak jak je
        return obj
    elif isinstance(obj, dict):
        # Pokud je dict, serializujeme rekurzivně všechny jeho hodnoty
        if recursive:
            output = {}
            for key, value in obj.items():
                output[key] = serialize(value, recursive)
            return output
        else:
            output = copy.copy(obj)  # Pokaždé chceme, abychom vraceli novou hodnotu
        return output
    elif isinstance(obj, list):
        # Pokud je list, serializujeme rekurzivně všechny jeho hodnoty
        if recursive:
            output = []
            for value in obj:
                output.append(serialize(value, recursive))
        else:
            output = copy.copy(obj)  # Pokaždé chceme, abychom vraceli novou hodnotu
        # obj = list(map(lambda x: serialize(x, True), obj))
        return obj
    else:
        type_ = type(obj)
        if isinstance(obj, Serializable):
            # Jinak se podíváme, jestli má Serializable protokol...
            # TODO: Donutit pyright, aby si odvodil typ... (TRawSerializableValue = RawSerializableValue)
            serialized = obj.serialize()
        elif type_ in _serializers:
            #  ... pokud ne, zkusíme registrované serializery ...
            serialized = _serializers[type_][0](obj)
        else:  # ... jinak výjimka
            raise exceptions.MissingSerializer(
                f"Žádný registrovaný serializer pro typ {type_}"
            )

        if recursive:
            if isinstance(serialized, (dict, list)):
                serialized = serialize(serialized, recursive)

        return {
            "__type__": get_full_type_name(type_),
            "data": serialized,
        }


@overload
def deserialize(data: TSerializablePrimitive) -> TSerializablePrimitive:
    ...


# Vracíme `Any`, jelikož k tomu jsou type checkery shovívavější jak k `object`
@overload
def deserialize(data: SerializedData | RawSerializedData, recusive: bool = True) -> Any:
    ...


@overload
def deserialize(data: SerializableValue, recusive: bool = True) -> RawSerializableValue:
    ...


def deserialize(
    data: SerializableValue | SerializedData | RawSerializedData, recusive: bool = True
) -> Any:

    if is_union(data, SerializablePrimitive):
        # Pokud je primitive, necháme tak jak je
        return data
    elif isinstance(data, dict):
        # Pokud je dict ...

        # Pro kompatibilitu s verzemi před BakalářiAPI 3.0
        # TODO: Bude odtraněno v jedné z následující verzích
        if "_type" in data:
            LOGGER.debug("Object have old structure, upgrading")
            data["__type__"] = data["_type"]  # type: ignore
            del data["_type"]  # type: ignore

        if is_typed_dict(data, SerializedData):
            # ... a zároveň je to (Raw)SerializedData TypedDict,
            # tak nejdříve zkotrolujeme, zda se jedná o komplexní serializaci ...
            if data["__type__"] == "/":
                # ... pokud ano, deserializujeme přes komplexní deserilizaci ...
                return complex_deserialize(data)
            # ... pokud ne, tak deserializujeme "vnořená" data ...
            if recusive:
                data["data"] = deserialize(data["data"], recusive)
            type_ = resolve_string(data["__type__"])
            if issubclass(type_, Serializable):
                # ... poté zkontrolujeme jestli typ implementuje Serializable protokol, ...
                return type_.deserialize(data["data"])
            if type_ in _serializers:
                # ... jinak zkotrolujeme, jestli je registrovený deserializer pro tento typ ...
                return _serializers[type_][1](data["data"])
            # ... a pokud ne, tak exception
            raise exceptions.MissingDeserializer(
                f"Žádný registrovaný deserializer pro typ {type_}"
            )
        else:
            # Pokud to nejsou SerializeData, zkusíme registrované serializery
            # `cast()`, protože z nějakého důvodu se `TypeGuard` stahuje jen na "if" blok a ne na
            # "elif" a "else" bloky. Takhle je to stanovený v PEP 647 a ani v Python mailing listu,
            # který řešil tenhle PEP, jsem nenašel důvod, proč tomu tak je eShrug
            data = cast(dict[str, SerializableValue], data)
            if recusive:
                for key, value in data.items():
                    data[key] = deserialize(value, recusive)
            return data
    elif isinstance(data, list):
        if recusive:
            for index, value in enumerate(data):
                data[index] = deserialize(value, recusive)
            # data = list(map(lambda x: deserialize(x, True), obj))
        return data
    raise ValueError


def complex_serialize(data: object) -> SerializedData:
    obj_list: list[SerializedData] = []

    def generate_ref(id: int) -> SerializedData:
        return {
            "__type__": "@",
            "data": id,
        }

    identity2id: dict[int, int] = {}

    def recursion(obj):
        # Jen kvůli optimalizaci, jelikož by stejně `SerializablePrimitive` skončil
        # v "else" větvi, odkud se jen vrátí (tzn., že to bude fungovat i bez tohoto)
        if is_union(obj, SerializablePrimitive):
            return obj

        # Pokud je už objekt serializovaný, znovu serializovat nebudeme
        if id(obj) in identity2id:
            return generate_ref(identity2id[id(obj)])

        serialized: SerializableValue | RawSerializedData = serialize(obj, False)

        if isinstance(serialized, dict):
            if is_typed_dict(serialized, RawSerializedData):
                identity2id[id(obj)] = len(obj_list)
                # Musíme přidat objekt do `obj_list` teď hned, ačkoli je v tuto chvíli
                # pořád ještě `RawSerializableData`. Resp. potřebujeme objket přidat
                # předtím, než spustíme další iteraci rekurze, jelikož jinak budou všechny
                # refence referencovat na objekt 0 (protože list bude pořád prázdný)
                obj_list.append(serialized)  # type: ignore # Na `SerializedData` se mění následují řádkou
                serialized["data"] = recursion(serialized["data"])
                return generate_ref(identity2id[id(obj)])
            else:
                for key, value in serialized.items():
                    serialized[key] = recursion(value)
                return serialized
        elif isinstance(serialized, list):
            for index, value in enumerate(serialized):
                serialized[index] = recursion(value)
            return serialized
        else:
            return serialized

    return {
        "__type__": "/",
        "data": {"objects": obj_list, "structure": recursion(data)},
    }


# Vracíme `Any`, jelikož k tomu jsou type checkery shovívavější jak k `object`
def complex_deserialize(data: SerializedData) -> Any:
    try:
        if "objects" not in data["data"] or "structure" not in data["data"]:  # type: ignore # Případné věci odchytáváme
            raise KeyError
    except (TypeError, KeyError) as e:
        raise ValueError("Data nebyla serializována skrze komplexní serializaci") from e
    original_obj_list: list[SerializedData] = data["data"]["objects"]  # type: ignore
    # Otáčíme list kvůli optimalizaci. Jelikož při serializaci dáváme do listu parrenty dřív jak childy,
    # tak bychom se parrenty snažili deseriaizovat dřív jak childy (kdybychom list neotočili) a to by
    # znamenalo, že bychom při deserializaci selhali. Př.:
    #   A má child B a B má child C. Po serializaci je list [A,B,C]. Při deserializaci bychom se pokusili
    #   deserializovat nejdříve A, což by nedopadlo, poté B, což znovu nepůjde a nakonec C, které konečně
    #   deserializovat můžeme. Při druhé iteraci bychom opět nemohli nic udělat s A, nýbrž jen s B. Vše
    #   by bylo deserializováno až při třetí iteraci.
    # Pokud ale list otočíme, tohle se nestane a vše lze deserializovat v jedné iteraci. Musíme ale
    # příslušně modifikovat `reference_id`, aby brali v potaz otočený list.
    original_obj_list = original_obj_list[::-1]
    real_obj_list: list[object] = [None] * len(original_obj_list)

    class NotDeserializedYet(Exception):
        def __init__(self, ref_id: int):
            self.ref_id = ref_id
            super().__init__()

    def recursion(data):
        if isinstance(data, dict):
            if is_typed_dict(data, SerializedData):
                # V tuhle chvíli to může být pouze reference, jelikož jinak by to byl samostaný objekt
                if data["__type__"] != "@":
                    raise ValueError(
                        f"Očekáván interní typ reference, ale nalezen typ '{data['__type__']}'"
                    )
                # Pokud si s daty nikdo nehrál, mělo by to být `int`
                reference_id = cast(int, data["data"])
                reference_id = len(original_obj_list) - 1 - reference_id
                LOGGER.debug(
                    "Při komplexní deserializaci byla nalezena reference na ID %s",
                    reference_id,
                )
                if real_obj_list[reference_id] is None:
                    raise NotDeserializedYet(reference_id)
                else:
                    return real_obj_list[reference_id]
            else:
                for key, value in data.items():
                    data[key] = recursion(value)
                return data
        elif isinstance(data, list):
            for index, value in enumerate(data):
                data[index] = recursion(value)
            return data
        else:
            return deserialize(data)

    # Nevyřešená reference z [0] na [1]
    last_unresolved: list[tuple[int, int]] = []
    while True:
        current_unresolved: list[tuple[int, int]] = []
        is_something_none = False
        for index, obj in enumerate(original_obj_list):
            if real_obj_list[index] is None:
                try:
                    deserialized = recursion(obj["data"])
                except NotDeserializedYet as e:
                    is_something_none = True
                    current_unresolved.append((index, e.ref_id))
                else:
                    real_obj_list[index] = deserialize(
                        {"__type__": obj["__type__"], "data": deserialized}, False
                    )
        if not is_something_none:
            break
        if current_unresolved == last_unresolved:
            # TODO: Podpora rekurze
            raise Exception("Detekována rekurze při deserializaci")
        else:
            last_unresolved = current_unresolved
            LOGGER.debug(
                "Nutná další iterace komplexní deserializace (počet nevyřešených objektů je %s)",
                len(current_unresolved),
            )

    return recursion(data["data"]["structure"])  # type: ignore


### Předdefinované serializery ###

# datetime
register(datetime, lambda x: x.isoformat(), datetime.fromisoformat)
# tuple
register(tuple, list, tuple)
