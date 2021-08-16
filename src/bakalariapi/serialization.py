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
import warnings
from datetime import datetime
from typing import Callable, Protocol, TypedDict, TypeVar, Union, runtime_checkable

from . import exceptions
from .utils import T0, T1, get_full_type_name, is_typed_dict, resolve_string

LOGGER = logging.getLogger("bakalariapi.serialization")


SerializableValue = Union[
    bool,
    dict[str, "SerializablePrimitive"],  # type: ignore # Mypy nepodporuje rekurzi  https://github.com/python/mypy/issues/731
    float,
    int,
    list["SerializablePrimitive"],  # type: ignore # Mypy nepodporuje rekurzi  https://github.com/python/mypy/issues/731
    None,
    str,
]
TSerializableValue = TypeVar("TSerializableValue", bound=SerializableValue)


class SerializedData(TypedDict):
    __type__: str
    data: SerializableValue


_serializers: dict[type, tuple[Callable, Callable]] = {}


def register(
    type_: type[T0],
    serializer: Callable[[T0], TSerializableValue],
    deserializer: Callable[[TSerializableValue], T0],
):
    _serializers[type_] = (serializer, deserializer)


def serialize(obj) -> SerializedData:
    type_ = type(obj)
    if isinstance(obj, Serializable):
        return {"__type__": get_full_type_name(type_), "data": obj.serialize()}
    if type_ in _serializers:
        return {
            "__type__": get_full_type_name(type_),
            "data": _serializers[type_][0](obj),
        }
    raise exceptions.MissingSerializer(f"Žádný registrovaný serializer pro typ {type_}")


def deserialize(data: SerializedData):
    type_ = resolve_string(data["__type__"])
    if issubclass(type_, Serializable):
        return type_.deserialize(data["data"])
    if type_ in _serializers:
        return _serializers[type_][1](data["data"])
    warnings.warn(
        exceptions.MissingDeserializer(
            f"Žádný registrovaný deserializer pro typ {type_}"
        )
    )


@runtime_checkable
class Serializable(Protocol[T1]):
    """Protokol, který implementují třídy, které jsou schopné serializace."""

    def serialize(self) -> T1:
        """Serializuje objekt tak, aby ho mohla následně metoda `.deserialize()` deserializovat."""
        raise NotImplementedError()

    @classmethod
    def deserialize(cls: type[T0], data: T1) -> T0:
        """Deserializuje data, které vyprodukovala `.serialize()` metoda."""
        raise NotImplementedError()


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

        if is_typed_dict(o, SerializedData):
            LOGGER.debug("Futher deserializing data:\n%s", o)
            return deserialize(o)

        return o


### Předdefinované serializery ###

# datetime
register(datetime, lambda x: x.isoformat(), lambda x: datetime.fromisoformat(x))
