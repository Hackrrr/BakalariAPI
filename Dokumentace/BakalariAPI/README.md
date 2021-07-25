# Úvod
Tato složka by měla poskytnout dokumentaci ohledně `BakalářiAPI` - jak s ním pracovat, jak funguje, nějaké termíny, které se (nejen) interně používají, či případně jak si `BakalářiAPI` upravit.

Konkrétně tento soubor by měl být návod, jak zprovoznit základ `bakalariapi` modulu.

# Inicializace
Celý `BakalářiAPI` se točí kolem třídy `bakalariapi.BakalariAPI`. Na začátek bychom měli vytvořit instanci této třídy:
```py
import bakalariapi
api = bakalariapi.BakalariAPI("https://bakalari.mojeskola.cz", "ÚžasněSkvěléJméno", "SuperTajnéHeslo")
```
Nyní máme připravenou instanci, přes/skrz kterou budeme dělat úplně vše.

První věc, co nejspíš budeš chtít udělat, je ověření funkčnosti serveru a správnost přihlašovacích údajů:
```py
if not api.is_server_running():
    raise Exception("Server není dostupný")
elif not api.is_login_valid():
    raise Exception("Nesprávné přihlašovací údaje")
```
Samozřejmě pokud jsi si jistý/jistá, že je vše správně, tak tyto metody volat nemusíš a ušetřit tím trochu času. Reálně toho času zase až tak moc neušetříš, jelikož sessiony se "recyklují" a použijí znova, aby se nemusel pro každou operaci vytvářet inicializovat nový session.

Další (potencionálně chtěný) krok je `.init()` metoda. Ta získá některé informace o serveru (`bakalariapi.ServerInfo`) a uživatelovi (`bakalariapi.UserInfo`). Pokud tyto informace vědět nepotřebuješ, tak s `.init()` metodou nemusíš ztrácet čas.
```py
api.init() # Tato metoda nic nevrací ...
print(api.user_info.hash) # ... ale ukládá data do UserInfo instance pod atributem "user_info" ...
print(api.server_info.version) # ... a do ServerInfo instance pod atributem "server_info"

if api.server_info.version != bakalariapi.LAST_SUPPORTED_VERSION:
    print("Jiná verze Bakalářů, některé funkce nemusí fungovat správně")
```
Doporučuji ale `.init()` volat, jelikož pak lze ověřit reálnou verzi Bakalářů oproti verzi Bakalářů v `bakalariapi`. Ačkoli pravděpodobně vše bude fungovat, je stejně lepší někde v aplikaci oznámit, že se mohou vyskytnout určité deviace.

# Získávání dat
Nyní ta zábavná část - samotné získání dat. K tomu opět využijeme naší `BakalariAPI` instanci v proměnné `api`. `BakalariAPI` má hromadu metod, jejichž název začíná slovem "get":
```py
api.get_grades(...)
api.get_homeworks(...)
api.get_meeting(...)
# ...
```
Tyto "get" metody nám slouží pro získávání dat. Všechny vrací array daných objektů (známky/úkoly/schůzky/...) a každá z těchto metod má jako první parametr "mode", typu `bakalariapi.GetMode` - jedná se o enum určující, jak se data získají - buď se získají v módu `GetMode.CACHED`, `GetMode.FRESH` nebo `GetMode.CACHED_OR_FRESH`. V módu `GetMode.CACHED` se načtou pouze data, která už jsou načtená (v looting instanci (viz dále)), takže se neprovede žádný dotaz na samotný server. Takže je možné, že data, která takto získáš, mohou být neaktuální. Naopak v módu `GetMode.FRESH` se data načtou čistě ze serveru, tudíž to nějaký čas zabere. A poslední mód, `GetMode.CACHED_OR_FRESH`, je kombinací obou dvou dohromady - nejdříve se zkusí načíst jako v módu `GetMode.CACHED` a pokud se žádná data nenačetla (teda počet vrácených objektů je 0), načtou se data v `GetMode.FRESH` módu. Takže když už teď víme, jak specifikovat výběr dat, můžeme nějaká získat:
```py
znamky = api.get_grades(bakalariapi.GetMode.CACHED_OR_FRESH)
# ========== Nebo ==========
from bakalariapi import GetMode # Pokud si chceme zkrátit zápis, tak můžeme importovat přímo GetMode ...
znamky = api.get_grades(GetMode.CACHED_OR_FRESH) # ... a tím pádem můžeme vynechat "bakalariapi."
```
Metody mít i další parametry. Pokud metoda má i další parametry, tak pak tyto parametry je možné vkládat pouze jako keyword argumenty, tedy že se jednotlivé parametry musí specifikovat jménem:
```py
komens_zpravy = api.get_komens(bakalariapi.GetMode.CACHED_OR_FRESH, limit = 10)
```
Ovšem zde pozor - Pokud použiješ mód `GetMode.CACHED_OR_FRESH` a data jsou již v looting instanci, tak se nehledí na další parametry. Tzn., že předchozí kód může vrátit mnohem víc výsledků, než jen 10 (parametr `limit` omezuje počet výsledků), jelikož se v minulosti již data načetly. Stejně tak se může stát, že pokud zde bude kupříkladu parametr `from_date` filtrující výsledky dle data, tak se vrátí i nechtěné výsledky, které jsou starší, než uvedený datum.

# Looting
Nyní, když už jsme získali nějaká data, možná by se hodilo mít větší kontrolu nad již získanými výsledky. Pojďme se tedy podívat na třídu `bakalariapi.Looting`.

Tato třída obstarává uchování výsledků. Většina věcí se děje "pod pokličkou" (v `bakalariapi.BakalariAPI` instanci), ale může nastat situace, kdy chceme mít k již získáním přímý (nebo spíš "přímější") přístup. K looting instanci lze přistoupit skrze `.looting` atribut na `bakalariapi.BakalariAPI` instanci. Z lootingu můžeme dostat všechny objekty jednoho typu pomocí `.get()` metody:
```py
znamky = api.looting.get(bakalariapi.Grade)
```
Tenhle kód by vrátil array všech objektů typu `bakalariapi.Grade` (= objekty známek). Tohle prakticky dělá `bakalariapi.BakalariAPI` instance "v utajení", když se získávají data v `GetMode.CACHED` módu.

Zajímavější ale je export a import dat. K tomu slouží metody `.export_JSON()` a `import_JSON()`, které nečekaně používají JSON formát. Zatím není možnost použít jiný formát, ale je možnost si udělat vlastní. Ale opět pozor - Import nahradí předchozí data, tudíž může dojít ke ztrátě dat.
```py
api.looting.import_JSON(
    api.looting.export_JSON()
)
```
Někdo by si mohl myslet, že tento kód prakticky nic neudělá. To by ale byl na omylu, jelikož toto může vést k neočekávanému chování:
- Export si neumí moc dobře poradit s referencemi na ostatní objekty. Pokud některý z objektů, který se serializuje, obsahuje referenci na jiný objekt, ve výsledném exportovaném JSONu bude tento referencovaný objekt "samostatný". Tzn., že pokud více objektů referencuje jeden a ten samý objekt *X*, v exportovaných datech bude každých z těchto objektů vlastní objekt *X* (který bude vypadat jako původní objekt *X*, ale z exportovaných dat nelze poznat, že všechny objekty odkazovaly na ten samý).
- Import logicky vytváří nové objekty (na základě dat, které importuje) a tyto nové objekty pak nahradí stará data v lootingu. Tudíž reference na objekty získané z lootingu před importem již nebudou ovlivňovat nové objekty (jedná o rozdílné objekty).

# Závěr
Tak to bylo takové "krátké" shrnutí jak použít `bakalariapi` modul. Nyní už stačí napsat nějaký kvalitní kód, který bude `bakalariapi` využívat.
