from __future__ import annotations

__all__ = [
    "register",
    "serialize",
    "deserialize",
    "complex_serialize",
    "complex_deserialize",
    "SerializedData",
    "Serializable",
    "SimpleSerializable",
    "Upgradeable",
]

import copy
import logging
from datetime import datetime
from typing import (
    Any,
    Callable,
    ClassVar,
    Literal,
    Mapping,
    Protocol,
    Sequence,
    TypedDict,
    TypeVar,
    Union,
    cast,
    overload,
    runtime_checkable,
)

from . import exceptions
from .utils import (
    T0,
    _CustomChecks,
    get_full_type_name,
    is_typed_dict,
    is_union,
    resolve_string,
)

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
    Sequence["SerializableValue"],  # type: ignore # Mypy nepodporuje rekurzi  https://github.com/python/mypy/issues/731
    "Serializable[Any]",
    "SerializedData",  # Kupodivu to funguje, ale čekám, že se to jednou zase rozbije
]
RawSerializableValue = Union[
    SerializableValue,
    Mapping[str, Any],
    Sequence[Any],
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


@runtime_checkable
class Upgradeable(Protocol, metaclass=_CustomChecks):
    deserialization_keys: ClassVar[set[str]]

    @classmethod
    def upgrade(
        cls,
        data: Mapping[str, Any],
        missing: set[str],
        redundant: set[str],
    ) -> Mapping[str, Any]:
        raise NotImplementedError()

    @classmethod
    def __subclasscheck__(cls, subclass):
        return hasattr(subclass, "deserialization_keys") and hasattr(
            subclass, "upgrade"
        )


class SimpleSerializable(Serializable[dict[str, Any]]):
    def serialize(self) -> dict[str, Any]:
        return dict(self.__dict__)

    @classmethod
    def deserialize(cls: type[T0], data: dict[str, Any]) -> T0:
        # Postaveno na základě tohoto https://stackoverflow.com/a/2169191
        obj = super().__new__(cls)  # type: ignore # https://github.com/python/mypy/issues/9282
        for k, v in data.items():
            # if hasattr(obj, k): # Nebude fungovat, jelikož nevoláme __init__, nýbrž pouze __new__ a tím pádem objekt nemá prakticky žádné atributy
            setattr(obj, k, v)
        return obj


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

        output = {}
        # Ale nejdříve escapujeme klíč "__type__" a klíče začínající "#",
        # aby se o to nemusel starat nikdo jiný... a tiše doufáme, že všechny
        # klíče jsou string
        # TODO: Non-string klíče
        for key in obj.keys():
            output[
                "#" + key if key == "__type__" or key.startswith("#") else key
            ] = obj[key]

        if recursive:
            for key, value in output.items():
                output[key] = serialize(value, recursive)

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
        return output
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
def deserialize(
    data: SerializedData | RawSerializedData, recursive: bool = True
) -> Any:
    ...


@overload
def deserialize(
    data: SerializableValue, recursive: bool = True
) -> RawSerializableValue:
    ...


def deserialize(
    data: SerializableValue | SerializedData | RawSerializedData, recursive: bool = True
) -> Any:
    if is_union(data, SerializablePrimitive):
        # Pokud je primitive, necháme tak jak je
        return data
    elif isinstance(data, dict):
        # Pokud je dict ...
        if is_typed_dict(data, SerializedData):
            # ... a zároveň je to (Raw)SerializedData TypedDict,
            # tak nejdříve zkotrolujeme, zda se jedná o komplexní serializaci ...
            if data["__type__"] == "/":
                # ... pokud ano, deserializujeme přes komplexní deserilizaci ...
                return complex_deserialize(data)
            # ... pokud ne, tak deserializujeme "vnořená" data.
            if recursive:
                data["data"] = deserialize(data["data"], recursive)
            type_ = resolve_string(data["__type__"])
            # Ověříme, zda je typ Upgradeable, případně upgradujeme.
            if isinstance(data["data"], Mapping) and issubclass(type_, Upgradeable):
                actual = set(data["data"].keys())
                missing = type_.deserialization_keys - actual
                redundant = actual - type_.deserialization_keys
                data["data"] = type_.upgrade(data["data"], missing, redundant)
            # Následně zkontrolujeme jestli typ implementuje Serializable protokol, ...
            if issubclass(type_, Serializable):
                # pokud ano, deserializujeme pomocí něj, ...
                return type_.deserialize(data["data"])
            # ... pokud ne, tak zkotrolujeme, jestli je registrovený deserializer pro tento typ ...
            if type_ in _serializers:
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

            # Odescapujeme klíče, které jsem escapovali při serializaci
            output = {}
            for key in data.keys():
                output[key[1:] if key.startswith("#") else key] = data[key]

            if recursive:
                for key, value in output.items():
                    output[key] = deserialize(value, recursive)
            return output
    elif isinstance(data, Sequence):
        output = [None] * len(data)
        for index, value in enumerate(data):
            output[index] = deserialize(value, recursive) if recursive else value  # type: ignore
            # Ignore, protože `output` si pyright odvodil jakožto `list[None]`... Jo...
            # Proč to není teda anotované třeba jako `list[Any]`? Protože tu je `output`,
            # i v jiné větvy (viz 10 řádků výš) a pyright si pak stěžuje, že dáváme `dict` do `list`u
        return output
    raise ValueError


class Reference(TypedDict):
    __type__: Literal["@"]
    data: int


class ReferenceData:
    reference: Reference
    count: int
    first_parent: Mapping | list | None
    first_key: str | int | None

    def __init__(
        self,
        reference: Reference,
        parent: Mapping | list | None,
        key: str | int | None,
    ):
        self.reference = reference
        self.count = 1
        self.first_parent = parent
        self.first_key = key

    def is_root_reference(self) -> bool:
        return self.first_parent == None


def complex_serialize(data: object, *, inlining: bool = True) -> SerializedData:
    # Poprvé, co potřebuji poctivě okomentovat kód, protože tady je to vážně potřeba...

    # Nejdříve deklarovat potřebné věci:
    #   - `obj_list` je list výsledných (serializovaných) dat
    #   - `references` je slovník uchovávající reference (resp. ReferenceData) dle identity daného
    #   objektu (v `obj_list`), na který ukazují (viz `get_ref()`)
    obj_list: list[SerializableValue] = []
    references: dict[int, ReferenceData] = {}

    # Pomocná funkce pro generování referencí.
    # Všechny reference na stejný index/objekt by měli být stejné, tzn. že na pro daný index/objekt
    # vytvoříme referenci jen jednou, v další případech vracíme již tu onu vytvořenou referenci.
    # Tohle je potřeba kvůli následému inliningu, abychom nemuseli prohledávat vše co jsme serializovali (viz inlining dále).
    def get_ref(
        identity: int,
        parent: Mapping | list | None,
        key: str | int | None,
        index: int | None = None,
    ) -> Reference:
        if identity in references:
            # Pokud reference již existuje, jen zaznamenáme, že je použita znovu
            references[identity].count += 1
        else:
            # Pokud reference na daný objekt ještě neexistuje, vytvoříme
            if index is None:  # type guard jen kvůli typingu
                raise ValueError()
            reference: Reference = {
                "__type__": "@",
                "data": index,
            }
            references[identity] = ReferenceData(reference, parent, key)
        return references[identity].reference

    # V podstatně serializace samotná
    def recursion(
        obj,
        upper_parent: Mapping | list | None,
        upper_key: str | int | None,
        nested: bool = False,
    ) -> SerializableValue:
        # Pokud je primitive, můžeme vrátit rovnou - serializovat nepotřebujeme, reference neřešíme
        if is_union(obj, SerializablePrimitive):
            return obj

        # Pokud je už objekt serializovaný, znovu serializovat nebudeme a vrátíme
        # referenci na již serializovaný objekt.
        # `upper_parent is not None` je optimalizace - pokud je `None`, tak je buď root
        # a nebo "`nested`" (viz dále) a v obou případech víme, že `id(obj) in references`
        # bude `False` a nemusíme kvůli tomu tedy prohledávát celý `references`.
        if upper_parent is not None and id(obj) in references:
            return get_ref(id(obj), upper_parent, upper_key)

        # "`nested`" je speciální případ, který nastane serializování `(Raw)SerializedData`.
        # Když serializujeme `SerializedData["data"]` nechceme vracet (ani vytvářet) referenci,
        # jelikož víme, že tenhle objekt bude jen jednou (protože je to objekt, který jsme
        # si vytvořili sami a my víme, že ho nikde jinde používat nebudeme).
        if not nested:
            # Pokud není "`nested`", vygenerujeme si referenci
            r = get_ref(id(obj), upper_parent, upper_key, -1)

        # Nyní serializujeme data a pokud výsledkem bude `list` nebo `dict`,
        # budeme volat `recursion()` na jejich hodnoty. Pokud bude výsledkem
        # `(Raw)SerializedData`, budeme volat `recursion(nested=True)` na klíč "data"
        serialized: SerializableValue | RawSerializedData = serialize(obj, False)

        if isinstance(serialized, list):
            # list
            for index, value in enumerate(serialized):
                serialized[index] = recursion(value, serialized, index)
        elif is_typed_dict(serialized, RawSerializedData):
            # RawSerializableData
            serialized["data"] = recursion(serialized["data"], None, None, True)
        elif isinstance(serialized, dict):
            # dict
            for key, value in serialized.items():
                serialized[key] = recursion(value, serialized, key)
        else:
            # Funkce `serialize()` by měla v tomto případě vždy vrátit list nebo slovník.
            # Teoreticky by měla vrátit `SerializableValue`. `SerializableValue` je ale buď
            # `SerializablePrimitive`, `dict` nebo `list`, a tak, protože `SerializablePrimitive`
            # vzniká serializací sama sebou a `SerializablePrimitive` filtrujeme na začátku,
            # nám zůstává pouze `dict` a `list`.
            # Čistě teoreticky by tady else větev nemusela být, ale je tu jakožto sanity check.
            raise RuntimeError("serialize() returned something else than list or dict")

        # Protoře RawSerializedData jsme kompltně serializovali
        # BTW tohle nelze dělat ve větvy s RawSerializedData, protože nejsme schopni
        # odstranit/nahradit typ z již utvořené anotace
        serialized = cast(Union[SerializableValue, SerializedData], serialized)

        # Když je "`nested`", nechceme referenci (viz výš) nýbrž samotný serializovaný objekt
        if not nested:
            r["data"] = len(obj_list)  # type: ignore # `r` possibly unbound
            obj_list.append(serialized)
            return r  # type: ignore # `r` possibly unbound
        else:
            return serialized

    # Spustíme serializaci
    recursion(data, None, None)

    # Nyní případný inlining
    if inlining:
        # `inlined` je list indexů `obj_list`u, které jsou/budou inlined
        inlined: list[int] = []
        # Kvůli optimalizaci chceme procházet reference seřazeně podle indexu na který odkazují
        for reference_data in sorted(
            references.values(), key=lambda x: x.reference["data"]
        ):
            reference_data = cast(ReferenceData, reference_data)
            # Jelikož objekty, které jsou/budou inlined odstraníme, tak musíme pozměnit indexy,
            # na které se odkazuje o tolik, kolik odstraníme objektů před referencovaným objektem,
            # což se rovná velikosti `inlined`, protože máme reference seřazené
            reference_data.reference["data"] -= len(inlined)
            if not reference_data.is_root_reference() and reference_data.count == 1:
                # `+ len(inilined)` protože potřebujme "neutralizovat" předchozí změnu
                referenced_index = reference_data.reference["data"] + len(inlined)
                # Tohle je samotný inlining objektu - na místo reference dáváme referencovaný objekt
                reference_data.first_parent[reference_data.first_key] = obj_list[referenced_index]  # type: ignore
                # Zaznamenání, že referencovaný objekt je již inlined
                inlined.append(referenced_index)

        # To co je inlined můžeme odstranit
        # Chceme to dělat od největšího, jelikož jinak by se vždy reindexoval list
        # což nechceme, protože výkon a navíc bychom museli počítat se změnou indexů
        for index in sorted(inlined, reverse=True):
            del obj_list[index]

    # Vracíme root komplexní serializace ("__type__" == "/")
    return {
        "__type__": "/",
        "data": obj_list,
    }


# Vracíme `Any`, jelikož k tomu jsou type checkery shovívavější jak k `object`
def complex_deserialize(data: SerializedData) -> Any:
    # Kompatibilita pro data před v4.0
    legacy: bool = False
    original_obj_list: list[SerializedData]
    if (
        isinstance(data["data"], dict)
        and "objects" in data["data"]
        and "structure" in data["data"]
    ):
        legacy = True
        original_obj_list = data["data"]["objects"][::-1] + [data["data"]["structure"]]  # type: ignore
    else:
        original_obj_list = data["data"]  # type: ignore

    real_obj_list: list[object] = [None] * len(original_obj_list)

    class NotDeserializedYet(Exception):
        def __init__(self, ref_id: int):
            self.ref_id = ref_id
            super().__init__()

    def recursion(data):
        if isinstance(data, dict):
            if is_typed_dict(data, SerializedData):
                if data["__type__"] == "@":
                    # Mělo by to být `int`, pokud to nikdo externě nezměnil
                    reference_index = cast(int, data["data"])
                    if legacy:
                        reference_index = len(original_obj_list) - 2 - reference_index
                    LOGGER.debug(
                        "Při komplexní deserializaci byla nalezena reference na ID %s",
                        reference_index,
                    )
                    if real_obj_list[reference_index] is None:
                        raise NotDeserializedYet(reference_index)
                    else:
                        return real_obj_list[reference_index]
                else:
                    try:
                        deserialized = recursion(data["data"])
                    except NotDeserializedYet as e:
                        raise e
                    else:
                        return deserialize(
                            {"__type__": data["__type__"], "data": deserialized}, False
                        )
            else:
                # Odescapujeme klíče, které jsem escapovali při serializaci
                output = {}
                for key in data.keys():
                    output[key[1:] if key.startswith("#") else key] = data[key]
                for key, value in output.items():
                    output[key] = recursion(value)
                return output
        elif isinstance(data, list):
            output = [None] * len(data)
            for index, value in enumerate(data):
                output[index] = recursion(value)  # type: ignore # Pyrightu se asi nelíbí dvojí deklarace `output` v kombinaci s tím, že si zde odvodí typ `list[None]`
            return output
        else:
            return deserialize(data)

    # Nevyřešená reference z [0] na [1]
    last_unresolved: list[tuple[int, int]] = []
    while True:
        current_unresolved: list[tuple[int, int]] = []
        is_everything_resolved = True
        for index, obj in enumerate(original_obj_list):
            if real_obj_list[index] is None:
                try:
                    deserialized = recursion(obj)
                except NotDeserializedYet as e:
                    is_everything_resolved = False
                    current_unresolved.append((index, e.ref_id))
                else:
                    real_obj_list[index] = deserialized
        if is_everything_resolved:
            break
        if current_unresolved == last_unresolved:
            # TODO: Podpora rekurze
            # Ok, tohle je o dost složitější, než jsem čekal... A ano, čekal jsem
            # to dost složité, ale ukazuje se, že toho je trochu víc, takže tuhle
            # featuru prozatím odkládám.
            # Až se jednou rozhodnu konečně tohle zprovoznit, tak to pravděpodobně
            # bude nějak takto:
            #   SerializableRecusion(Serializable):
            #       @classmethod
            #       def early_deserialization(cls, serialized: RawSerializedData, unresolved_obj: RawSerializedData) -> RawSerializedData: ...
            #       def late_deserialization(self: T0, unresolved_obj: RawSerializedData, resolved_obj: object) -> T0: ...
            # Kde:
            #   `serialized@early_deserialization` je ten daný objekt, který se snažíme deserializovat,
            #   `unresolved_obj@early_deserialization` je nedeserializovaný objekt, na který tento objekt odkazuje,
            #   `early_deserialization` vrací upravený `serialized@early_deserialization`, který lze potencionálně hodit do `deserialize`,
            #   `unresolved_obj@late_deserialization` je stejný objekt jako `unresolved_obj@early_deserialization`,
            #   `resolved_obj@late_deserialization` je deserializaovaný `unresolved_obj@late_deserialization`,
            #   a kde `late_deserialization` vrací upravený deserializovaný objekt                  .
            # Takhle je načrtnuto budoucí API, ale jelikož nemám žádný objekt,
            # u kterého bych potřeboval deserializovat rekurzi, tak nevím,
            # jestli je takového API vhodné a v tuto chvíli je tedy pro mě toto
            # featura s nízkou prioritou. (Navíc mám tušení, že se něco extrémně
            # pokazí (jako vždy) a nebude to tak pěkné, jak jsem tady načrtl.)
            raise RecursionError(
                f"Detekována rekurze při deserializaci ({current_unresolved})"
            )
        else:
            last_unresolved = current_unresolved
            LOGGER.debug(
                "Nutná další iterace komplexní deserializace (počet nevyřešených objektů je %s)",
                len(current_unresolved),
            )

    return real_obj_list[-1]


### Předdefinované serializery ###

# datetime
register(datetime, lambda x: x.isoformat(), datetime.fromisoformat)
# tuple
register(tuple, list, tuple)
# set
register(set, list, set)
# type
# register(type, get_full_type_name, resolve_string)
# Proč ne? Protože tohle zavání možností "exploitu", jelikož `resolve_string`
# klidně vrátí `os.system` a pokud s kód přepokládá callable objekt, tak to
# může dopadnout hodně špatně
