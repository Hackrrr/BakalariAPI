from __future__ import annotations

__all__ = [
    "register",
    "serialize",
    "deserialize",
    "SerializedData",
    "Serializable",
    "JSONSerializer",
    "JSONDeserializer",
]

import json
import logging
from datetime import datetime
from typing import (
    Any,
    Callable,
    Literal,
    Protocol,
    TypedDict,
    TypeVar,
    Union,
    cast,
    get_args,
    overload,
    runtime_checkable,
)

from . import exceptions
from .utils import T0, get_full_type_name, is_typed_dict, resolve_string

LOGGER = logging.getLogger("bakalariapi.serialization")

SerializablePrimitive = Union[
    bool,
    float,
    int,
    None,
    str,
]
SerializableValue = Union[  # `SerializableValue` je i `SerializedData`, jelikož `SerializedData` je `dict[str, "SerializableValue"]`
    SerializablePrimitive,
    dict[str, "SerializableValue"],  # type: ignore # Mypy nepodporuje rekurzi  https://github.com/python/mypy/issues/731
    list["SerializableValue"],  # type: ignore # Mypy nepodporuje rekurzi  https://github.com/python/mypy/issues/731
]
RawSerializableValue = Union[  # `RawSerializableValue` je i `RawSerializedData`, jelikož `RawSerializedData` je `dict[str, Any]`
    SerializableValue,
    dict[str, Any],
    list[Any],
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


@overload
def serialize(obj: TSerializablePrimitive) -> TSerializablePrimitive:
    ...


@overload
def serialize(obj: RawSerializableValue) -> SerializableValue:
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

    if isinstance(obj, get_args(SerializablePrimitive)):
        # Pokud je primitive, necháme tak jak je
        return obj  # type: ignore # pyrigh nechápe get_args, mypy se někde ztratilo LULW TODO: Tenhle ignore
    elif isinstance(obj, dict):
        # Pokud je dict, serializujeme rekurzivně všechny jeho hodnoty
        for key, value in obj.items():
            obj[key] = serialize(value)
        return obj
    elif isinstance(obj, list):
        # Pokud je list, serializujeme rekurzivně všechny jeho hodnoty
        for index, value in enumerate(obj):
            obj[index] = serialize(value)
        # obj = list(map(lambda x: serialize(x, True), obj))
        return obj
    else:
        type_ = type(obj)
        if isinstance(obj, Serializable):
            # Jinak se podíváme, jestli má Serializable protokol...
            serialized = (
                obj.serialize()
            )  # TODO: Donutit pyright, aby si odvodil typ... (TRawSerializableValue = RawSerializableValue)
        elif type_ in _serializers:
            #  ... pokud ne, zkusíme registrované serializery ...
            serialized = _serializers[type_][0](obj)
        else:  # ... jinak výjimka
            raise exceptions.MissingSerializer(
                f"Žádný registrovaný serializer pro typ {type_}"
            )

        if recursive:
            if isinstance(serialized, (dict, list)):
                serialized = serialize(serialized)

        return {
            "__type__": get_full_type_name(type_),
            "data": serialized,
        }


@overload
def deserialize(data: TSerializablePrimitive) -> TSerializablePrimitive:
    ...


@overload
def deserialize(data: SerializedData | RawSerializedData) -> object:
    ...


@overload
def deserialize(data: SerializableValue) -> RawSerializableValue:
    ...


def deserialize(data: SerializableValue | SerializedData | RawSerializedData) -> object:

    if isinstance(data, get_args(SerializablePrimitive)):
        # Pokud je primitive, necháme tak jak je
        return data  # type: ignore # pyrigh nechápe get_args, mypy se někde ztratilo LULW TODO: Tenhle ignore
    elif isinstance(data, dict):
        # Pokud je dict ...
        if is_typed_dict(data, SerializedData):
            # ... a zároveň je to (Raw)SerializedData TypedDict, ...
            type_ = resolve_string(data["__type__"])
            if issubclass(type_, Serializable):
                # ... tak zkontrolujeme jestli typ implementuje Serializable protokol, ...
                return type_.deserialize(data["data"])
            if type_ in _serializers:
                # ... jinak zkotrolujeme, jestli je registrovený deserializer pro tento typ ...
                return _serializers[type_][1](data["data"])
            # ... a pokud ne, tak exception
            raise exceptions.MissingDeserializer(
                f"Žádný registrovaný deserializer pro typ {type_}"
            )
        else:
            # Pokud
            # `cast()`, protože z nějakého důvodu se `TypeGuard` stahuje jen na "if" blok a ne na
            # "elif" a "else" bloky. Takhle je to stanovený v PEP 647 a ani v Python mailing listu,
            # který řešil tenhle PEP, jsem nenašel důvod, proč tomu tak je eShrug
            data = cast(dict[str, SerializableValue], data)
            for key, value in data.items():
                data[key] = deserialize(value)
            return data
    elif isinstance(data, list):
        for index, value in enumerate(data):
            data[index] = deserialize(value)
        # data = list(map(lambda x: deserialize(x, True), obj))
        return data
    raise ValueError


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


# JSON


class JSONSerializer(json.JSONEncoder):
    def default(self, o):
        try:
            return serialize(o)
        except exceptions.MissingSerializer:
            return super().default(o)


class JSONDeserializer(json.JSONDecoder):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, object_hook=self.hook, **kwargs)

    def hook(self, o):
        # Pro kompatibilitu s verzemi před BakalářiAPI 3.0
        # TODO: Bude odtraněno v jedné z následující verzích
        if isinstance(o, dict) and "_type" in o:
            LOGGER.debug("Object have old structure, upgrading")
            o["__type__"] = o["_type"]
            del o["_type"]

        if is_typed_dict(o, RawSerializedData):
            LOGGER.debug("Futher deserializing data:\n%s", o)
            return deserialize(o)

        return o


### Předdefinované serializery ###

# datetime
register(datetime, lambda x: x.isoformat(), lambda x: datetime.fromisoformat(x))
# tuple
register(tuple, lambda x: list(x), lambda x: tuple(x))
