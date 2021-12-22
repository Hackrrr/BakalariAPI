# Serializace
`BakalářiAPI` má vlastní poměrně komplexní systém serializace. Tento systém podporuje serializaci vlastních objektů, rekurze a referencí na objekty. Všechny funkce a třídy sloužící k serializaci jsou v modulu `serialization`.

# Co dělá serializace
Samotný systém nedokáže převést data do zapsatelné podoby, nýbrž převádí data do podoby, kterou dokáží jiné serializery zpracovat. Při serializaci se data převedou tak, aby nakonec data byla typu `SerializableValue` (= `Union` typů, které považujeme za serializovatelné). `SerializableValue` je buď `Mapping[str, SerializableValue]` (= `dict`), `Sequence[SerializableValue]` (= `list`) anebo `SerializablePrimitive` (= `Union[bool, float, int, None, str]`= typy, které by měli být serializovatelné každým serializerem).

Tzn., pokud chceme uchovat data ve formátu JSON:
```py
from bakalariapi.serialization import serialize
import json

data = [(0,1,2), {"a": "A"}]

serialized = serialize(data) # Nejdříve serializujeme pomocí `serialization` modulu 
json_data = json.dumps(serialized) # Poté využijeme JSON serializer
print(json_data)
```
Kdyby se zde nepoužila funkce `serialize()`, tak v tomto případě by `json` modul dokázal data serializovat, ale data by byla pozměněna - `tuple` by se změnil na `list`. Tento problém je vyřešen funkcí `serialize()` - data vrácená funkcí vypadají takto:
```py
[
    { # původně `tuple`
        "__type__": "builtins.tuple",
        "data": [0, 1, 2]
    },
    {"a": "A"}
]
```
Takto upravená data `json` již nijak nealternuje. Tady se ale již projevuje nejvýraznější nevýhoda - podstatně se nám zvětšil objem dat. To je ovšem cena, kterou tato serializace má, když chceme zachovat informaci, že je to `tuple`.

# Formát serializovaných objektů
Jak je znázorněno v příkladu, tak původní `tuple` se nám změnil na `dict`. Tento `dict` je v rámci `serialization` modulu označován jakožto `SerializedData` a jeho struktura je:
```py
{
    "__type__": "cely.nazev.typu",
    "data": SerializableValue
}
```
`"__type__"` je celý název daného typu. V `BakalářiAPI` se tento název získává skrze `utils.get_full_type_name()`. `"data"` jsou libovolná data, pomocí kterých lze objekt (daného typu) následně deserializovat.

Co se stane, když ale bude chtít serializovat `dict`, který má podobu `SerializedData`? Např. aplikace bude přidávat do `dict` klíče dle uživatele, který "omylem" přidá klíč `"__type__"`. Pokud takováto situace nastane, tak při serializaci se klíč upraví na `"#__type__"`. V důsledku toho se stejný způsobem (tedy přidáním `"#"`) upraví i klíče začínající na `"#"`. Při deserializaci, pokud má klíč první znak `"#"`, tak se o tento první znak zkrátí.

# (De)serializace objektů
Objekty, které nejsou `SerializableValue` se musí také nějak (de)serializovat. Buď, pokud implementují `Serializable` protokol, se (de)serializují pomocí vlastní metody, nebo pokud je pro typ objektu registrován (de)serializer, se (de)serializují pomocí něj. Pokud nelze provést ani jednu z těchto možností, nastane `exceptions.MissingSerializer` (nebo `exceptions.MissingDeserializer`).

## `Serializable`
Protokol `Serializable` definuje 2 metody - `.serialize()`, která by měla vrátit něco, co serializace umí převést na `SerializableValue` (takováto hodnota je označována jako `RawSerializableValue`) a `.deserialize()`, která by měla být schopná poskládat daný objekt z dat vrácených `.serialize()` metodou.

Pro jednoduchost je vytvořena třída `SimpleSerializable` implementující `Serializable` protokol, ze které lze dědit a získat tak základní schopnost (de)serializace. Funkčnost `.serialize()` metody je realizována pomocí `.__dict__`, takže je zajištěna serializace všech atributů objektu, alespoň ve většině případů. V implementaci `.deserialize()` metody je už trocha magie, protože nemůžeme jen tak vytvořit objekt z ničeho a musíme šáhnout na metodu `.__new__()`, která nám vytvoří základ, do kterého pak dáváme atributy skrze `setattr()`. Ačkoli to z toho plyne, tak to zmíním specificky - `.__init__()` metoda při deserializaci volána nebude. Pokud je potřeba provést nějaké operace po deserializaci, nejvhodnější způsob je pravděpodobně override `.deserialize()` metody.

## Registrované (de)serializery
Druhý způsob jak (de)serializovat objekty je přes registrované (de)serializery. Pokud se při (de)serializaci zjistí, že daný objekt neimplementuje `Serializable` protokol, systém se podívá, zda je pro typ objektu registrován (de)serializer a pokud ano, tak ho užije. Registrace je realizována funkcí `register()`. Př.:
```py
#      typ   serializer   deserializer
#        \        |       /
register(tuple, list, tuple)
```
Tento příklad je vzatý z předregistrovaných (de)serializerů, které jsou umístěny na konci [`serialization.py`](/src/bakalariapi/serialization.py) a určuje cestu, jak serializovat `tuple` instance (jinak řečeno - určuje, že se `tuple` instance mají převést na `list`).

# Komplexní serializace
Nyní komplexní serializace. Tak se nazývá serializace skrze funkci `complex_serialize()`. Tohle je to nejzajímavější, co serializace umí a to schopnost serializovat reference. Co se tím myslí? Dejme tomu, že chceme serializovat takováto data:
```py
obj = {"a": "A", "b": "B"}
data = [obj, obj]
serialized = serialize(data)
```
Po provedení bude proměnná `serialized` vypadat takto:
```py
[
    {"a": "A", "b": "B"},
    {"a": "A", "b": "B"}
]
```
Ok, máme duplicitní data, ale to není problém, který se snaží komplexní serializace řešit, ačkoli je to vedlejší efekt, pokud by nám šlo o redukci velikosti dat (tím, že odstraníme duplicity), tak komplexní serializace si v tomto případě povede hůře než normální. Problém, kvůli kterému byla komplexní serializace stvořena, jsou reference. Pokud bychom totiž nyní proměnnou `serialized` deserializovali, dostali bychom 2 různé objekty:
```py
deserialized = deserialize(serialized)

# Deserializované objekty jsou sice ekvivalentní, ale nejsou identické
deserilized[0] == deserilized[1] # True
deserilized[0] is deserilized[1] # False
# Původní objekty jsou samozřejmě (stále) identické
data[0] is data[1] # True
```
Pokud na serializování použijeme komplexní serializaci (`complex_serialize()`), serializovaná data budou vypadat takto (vysvětlení struktury bude následovat):
```py
{
    "__type__": "/",
    "data": [
        {"a": "A", "b": "B"},
        [
            {"__type__": "@", "data": 0},
            {"__type__": "@", "data": 0}
        ]
    ]
}
```
A pokud bychom nyní data deserializovali, objekty by byly identické:
```py
deserialized = complex_deserialize(serialized)

deserilized[0] is deserilized[1] # True
```
Pro deserializaci lze zde použít "normální" `deserialize()` funkci, která při detekování komplexní serializace (`"__type__" == "/"`) zavolá `complex_deserialize()`.

## Struktura komplexní serializace
Výstup komplexní serializace je již zmiňovaný `SerializedData`. Klíč `"__type__"` je `"/"` a pod klíčem `"data"` je list objektů. Každému objektu, který se při komplexní serializaci serializoval, náleží nějaký index v tomto listu. Díky tomu lze referencovat jednotlivé objekty v rámci serializovaných dat. Takováto reference je realizována pomocí dalšího `SerializedData` - klíč `"__type__"` je tentokrát `"@"` a `"data"` uchovává index objektu v listu objektů. Takže když vezeme předchozí příklad, tak reference `{"__type__": "@", "data": 0}` říká, že objekt, kterým se má při deserializaci nahradit, se nachází na indexu `0`.

## Inlining
Jakožto "inlining" je nazván proces, který probíhá po komplexní serializaci (lze vypnout parametrem `inlining=False`). V rámci tohoto procesu jsou reference na objekty, které je referencovány pouze jednou, nahrazeny tímto objektem. Jinak řečeno - pokud existuje na objekt pouze jedna reference, tak tato reference je nahrazena tím objektem. K čemu je to dobré? K redukci velikosti výstupu. Velikost se sníží přibližně o 10-20%, ale záleží, jaká je struktura dat, které se serializují - v nejhorším případě inlining nic neudělá, v nejlepším by klidně mohl snížit o ~100% (pro oba tyto případy by struktura musela být hodně specifická (hlavně pro těch ~100%); pochybuji, že se v praxi taková struktura vyskytne).

# `Upgradeable`
Poslední věc, co je v rámci serializace je protokol `Upgradeable`. Dejme tomu, že si serializujeme nějaká data, uložíme a necháme si je do budoucna. Problém ale nastane, pokud do doby, než je znovu načteme, změníme strukturu objektů, které jsme serializovali (např. změníme název atributu). Pokud bychom zkusili data deserializovat, tak v lepším nastane nějaká výjimka (pravděpodobně `AtributeError`), v horším případě vše proběhne v pořádku, ale vzniknou nám objekty, které nebudou správné (budou mít atributy, které by mít neměli, a naopak). Kvůli tomuto problému byl vytvořen protokol `Upgradeable`.

Implementace protokol spočívá ve vytvoření "statického" atributu `deserialization_keys` a class metody `.upgrade()`. `deserialization_keys` je `set` stringů, ve kterém je uložen seznam klíčů, které by objekt při deserializaci měl mít. Z toho také plyne, že metoda `.serialize()` musí vracet slovník. Metoda `.upgrade()` pak bere 3 argumenty:
- `data` - Slovník objektu v serializovaných datech pod klíčem `"data"`
- `missing` - `set` klíčů, které ve slovníku chybí oproti `deserialization_keys`
- `redundant` - `set` klíčů, které jsou slovníku navíc oproti `deserialization_keys`

`.upgrade()` by měla vracet slovník (pravděpodobně upravený slovník z argumentu `data`). Třída implementující `Upgradeable` by mohla vypadat třeba takto:
```py
class MojeTrida(Upgradeable): # Nejspíše (téměř jistě) se v praxi bude implementovat i `Serializable`, ale pro stručnost jsem to tu vynechal
    deserialization_keys: set = {"novy_atribut"}

    @classmethod
    def upgrade(cls, data: dict, missing: set, redundant: set) -> dict:
        if "novy_atribut" in missing:
            if "stary_atribut" in redundant:
                data["novy_atribut"] = data["stary_atribut"]
                del data["stary_atribut"]
            else:
                data["novy_atribut"] = 42
        
        return data
```

`.upgrade()` metoda se volá pokaždé, nehledě na to, zda existuje nějaký chybějící či redundantní klíč.

## `TypeError`: metaclass confilict
Při derivování z `Upgradeable` protokolu může Python vyhodit chybu `TypeError: metaclass conflict: the metaclass of a derived class must be a (non-strict) subclass of the metaclasses of all its bases` a v tu chvíli je problém, protože si nejspíše hraješ s metatřídami a protože já to dělám taky.

Pokud sis vytvořil(a) vlastní metatřídu, tak pro řešení se podívej na konec souboru [`utils.py`](/src/bakalariapi/utils.py), kde se nachází metatřída `_CustomChecks`, která je jedním z viníků tohoto problému - nad ní je "krátké" povídání, proč a k čemu je a jak je tento problém (ne)vyřešen.

Jednoho dne snad udělám nějaký hack, který tohle řešit bude, zatím tomu tak ale není.
