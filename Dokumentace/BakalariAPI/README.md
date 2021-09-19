# Úvod
Tato složka by měla poskytnout dokumentaci ohledně `BakalářiAPI` - jak s ním pracovat, jak funguje, nějaké termíny, které se (nejen) interně používají, či případně jak si `BakalářiAPI` upravit.

Konkrétně tento soubor by měl být návod, jak zprovoznit základ `bakalariapi` modulu.

# Inicializace
Celý `BakalářiAPI` se točí kolem třídy `bakalariapi.BakalariAPI`. Na začátek by se měla vytvořit instanci této třídy, která bude potřeba prakticky pro každou operaci:
```py
import bakalariapi
api = bakalariapi.BakalariAPI("https://bakalari.mojeskola.cz", "ÚžasněSkvěléJméno", "SuperTajnéHeslo")
```
Pokud nelze poskytnout argumenty při tvorbě instance, lze je vypustit a instance bude v "partial init módu". V tomto módu bude `BakalářiAPI` pracovat pouze offline. Argumenty lze doplnit později:
```py
import bakalariapi
api = bakalariapi.BakalariAPI()
api.server_info.url = "https://bakalari.mojeskola.cz"
api.username = "ÚžasněSkvěléJméno"
api.password = "SuperTajnéHeslo"
```

Následně lze ověřit funkčnost serveru a správnost přihlašovacích údajů:
```py
if not api.is_server_running():
    raise Exception("Server není dostupný")
elif not api.is_login_valid():
    raise Exception("Nesprávné přihlašovací údaje")
```
Samozřejmě toto lze přeskočit a ušetřit tím trochu času avšak reálně toho času zase až tak moc neušetříš, jelikož sessiony se "recyklují" a použijí znova, aby se nemusel pro každou operaci inicializovat nový session.

Další (potencionálně chtěný) krok je `.init()` metoda. Ta získá některé informace o serveru (`bakalariapi.ServerInfo`) a uživatelovi (`bakalariapi.UserInfo`). Pokud tyto informace jsou nepodstatné, lze opět `.init()` metodou vynechat.
```py
api.init() # Tato metoda nic nevrací ...
print(api.user_info.hash) # ... ale ukládá data do UserInfo instance pod atributem "user_info" ...
print(api.server_info.version) # ... a do ServerInfo instance pod atributem "server_info"

if not api.is_version_supported(): # Metoda, která ověřuje kompatibilitu BakalářiAPI
    print("Jiná verze Bakalářů, některé funkce nemusí fungovat správně")
```
Doporučuji ale `.init()` volat, jelikož pak lze ověřit reálnou verzi Bakalářů oproti verzi Bakalářů v `bakalariapi`. Ačkoli pravděpodobně vše bude fungovat, je stejně lepší někde v aplikaci oznámit, že se mohou vyskytnout určité deviace.

# Získávání dat
Nyní ta zábavná část - samotné získání dat. Instance třídy `BakalariAPI` má hromadu metod, jejichž název začíná slovem "get":
```py
api.get_grades(...)
api.get_homeworks(...)
api.get_meeting(...)
# ...
```
Tyto "get" metody slouží pro získávání dat. Všechny vrací list daných objektů (známky/úkoly/schůzky/...) a každá z těchto metod má jako první parametr "mode", typu `bakalariapi.GetMode` - jedná se o enum určující, jak se data získají - buď se získají v módu `GetMode.CACHED`, `GetMode.FRESH` nebo `GetMode.CACHED_OR_FRESH`. V módu `GetMode.CACHED` se načtou pouze data, která už jsou načtená (v `Looting` instanci (viz dále)), takže se neprovede žádný dotaz na samotný server. Tudíž je možné, že data, která takto získáš, mohou být neaktuální. Naopak v módu `GetMode.FRESH` se data načtou čistě ze serveru, tudíž to nějaký čas zabere. A poslední mód, `GetMode.CACHED_OR_FRESH`, je kombinací obou dvou dohromady - nejdříve se zkusí načíst jako v módu `GetMode.CACHED` a pokud se žádná data nenačetla (teda počet vrácených objektů je 0), načtou se data v `GetMode.FRESH` módu.
```py
znamky = api.get_grades(bakalariapi.GetMode.CACHED_OR_FRESH)
# ========== Nebo ==========
from bakalariapi import GetMode # Doporučuji alespoň trochu zkrátit
znamky = api.get_grades(GetMode.CACHED_OR_FRESH)
```
Metody mít i další parametry. Pokud metoda má i další parametry, tak pak tyto parametry je možné vkládat pouze jako keyword argumenty, tedy že se jednotlivé parametry musí specifikovat jménem:
```py
komens_zpravy = api.get_komens(bakalariapi.GetMode.CACHED_OR_FRESH, limit = 10)
```
Ale pozor - pokud se užije mód `GetMode.CACHED_OR_FRESH` a data jsou již v `Looting` instanci, tak se nehledí na další parametry. Tzn., že předchozí kód může vrátit mnohem víc výsledků, než jen 10 (parametr `limit` omezuje počet výsledků), jelikož se v minulosti již data načetly. Stejně tak se může stát, že pokud zde bude kupříkladu parametr `from_date` filtrující výsledky dle data, tak se vrátí i nechtěné výsledky, které jsou starší, než uvedený datum.

# Looting
Nyní třída `bakalariapi.Looting`, která obstarává uchování výsledků. Většina věcí se děje "pod pokličkou" (v `bakalariapi.BakalariAPI` instanci), ale může nastat situace, kdy chceme mít k již získáním přímý (nebo spíš "přímější") přístup. Přistoupit k nim lze skrz atribut `.looting` na `BakalariAPI` instanci. Z lootingu lze dostat všechny objekty jednoho typu pomocí `.get()` metody:
```py
znamky = api.looting.get(bakalariapi.Grade) # Vratí list objektů známek
```
Tohle prakticky dělá `bakalariapi.BakalariAPI`, když se získávají data v `GetMode.CACHED` módu.

Zajímavější ale je export a import dat. K tomu slouží metody `.export_data()` a `.import_data()`. `BakalářiAPI` kompletně vlastní systém serializace a popisovat ho zde postrádá smysl. Stačí vědět, že metoda `.export_data()` převede všechny data v `Looting` instanci na slovník, který by se měl dát serializovat do jakéhokolli formátu a metoda `.import_data()` naopak tento slovník bere a přidá jeho data k současným (to jak se přidávají data k sobě je také téma na někdy jindy). Jednoduchá (de)serializace do/z JSONu by teda vypadala takto:
```py
import json
with open("data.json") as soubor:
    json.dump(soubor, api.looting.export_data()) # Serializace
    api.looting.import_data(json.load(soubor)) # Deserializace
```

# Závěr
Tak to bylo takové "krátké" shrnutí jak použít `bakalariapi` modul. Nyní už stačí napsat nějaký kvalitní kód, který bude `bakalariapi` využívat.
