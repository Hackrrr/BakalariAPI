# Internal
Zde napíšu něco o tom, jak `BakalářiAPI` funguje interně. Pokud nechcete psát kód, který využívá "low-level" věci, tak tento dokument není potřebný.

# Sessiony
## BakalariSession
Sessiony jsou objekty, přes které děláme requesty na samotné Bakaláře. Sessiony jsou instance tříd derivovaných z `bakalariapi.sessions.BakalariSession`. Celkově jsou (zatím) 2 třídy sessionů - `RequestsSession` a `SeleniumSession`. Tyto druhy sessionů dělají takový "wrapper" daných modulů - tedy `RequestsSession` používá `requests` modul a `SeleniumSession` používá `selenium`.

Proč máme víc druhů sessionů? Jak bylo již několikrát zmíněno, tak důvodem jsou ASP.NET formuláře. Proč se tedy nepoužije jen `selenium`? Protože `selenium` je extrémně pomalý (zvětší části kvůli tomu, že Bakaláři jsou pomalý).

Asi nejdůležitější věc, co je u sessionů, je `busy` "flag" (vlastnost/atribut). `busy` indikuje, zda je session zrovna volný či ho nějaká část kódu někde zrovna používá. Nikdy by nikdo neměl manuálně nastavovat `busy` na `True` - o to by se měl starat `SessionManager` (viz dále) či sám session, když je použit jakožto kontextový manažer. Pokud ale i přesto z nějakého důvodu je potřeba tuto operaci provést manuálně, je velice silně doporučeno toto dělat v nějaké thread-safe části kódu. Pokud session není použit jako kontextový manažer, **musí** se manuálně nastavit `busy` jako `False`, poté co se sessionem přestalo pracovat, jinak tento session bude nadále považován za zaneprázdněný a tím pádem nikdy nedojde k jeho znovu užití.

Avšak pokud vytváříte nějaké low-level věci a instance sessionů si vytváříte sami (a tím pádem zcela ignorujete `SessionManager`), tak `busy` nemusíte řešit. Prakticky je tu `busy` flag jen pro `SessionManager`a a v rámci samotný sessionů se hodnota `busy` vůbec neřeší.

## SessionManager
Sessiony obstarává `bakalariapi.sessions.SessionManager`. Na něj směřují požadavky ohledně sessionů. `SessionManager` udržuje všechny sessiony, které má na starost - když se od `SessionManager`u vyžádá session, podívá se, jestli nemá náhodou pod správou nějaký volný session (tzn. session, který má `busy` nastaveno jako `False`) - když má, vrátí ten, když ne, vytvoří nový a vrátí tento nově vytvořený. `SessionManager` je napsán jakožto thread-safe, aby nedošlo k situaci, kdy se bude vyžadovat session ze dvou míst najednou a vrátil by jeden a ten samý dvakrát.

V přechozí části bylo něco o hodnotě `busy`. Defaultně `SessionManager` při vracení sessionů automaticky nastavuje `busy` flag (jelikož defaultní hodnota argumentu `set_busy` je `True`), takže je vždy zaručeno, že session nepoužije nikdo jiný (do té doby, než začne někdo šahat na `busy` flag přičemž ten někdo neví, co dělá). Pokud z nějakého důvodu je potřeba, aby `SessionManager` nenastavoval `busy` na `True`, stačí nastavit argument `set_busy` na `False`.

# Získání a zpracování dat
## Gettery
"Gettery" jsou funkce, které udělají request(y) na Bakaláře a vrátí `GetterOutput` (viz dále).
Tohle je asi nejméně standardizovaná část ze všech. Při začátku reworku na moduly zde byla idea o statických metodách/dekorátorech `_get(Endpoint)` a `_register_getter(getter_func)` (stejně tak jako u třeba parserů (viz dále)) na `BakalariAPI` třídě, ale vzhledem k velké variaci parametrů u "getter" funkcí to nedopadlo. Většina getterů vypadá nějak takto:
```py
def getter(api: BakalariAPI) -> GetterOutput[dict]:
    with api.session_manager.get_session_or_create(RequestsSession) as session: # Získání sessionu
        # Session je zde použit jako kontextový manažer, takže řešení hodnoty `busy` je zcela automatické
        response = session.get(api.get_endpoint(Endpoint.NĚJAKÝ_ENDPOINT)).json() # Request a dekódování JSON data
    return GetterOutput(Endpoint.NĚJAKÝ_ENDPOINT, response) # Výstup
```
Jelikož, jak zde již bylo zmíněno, nejsou gettery standardizované, tak není ani nějaká pěkná cesta, jak je volat. Proto se volají přímo skrz moduly.
## GetterOutput
`GetterOutput` (`bakalariapi.looting.GetterOutput`) je třída, která obsahuje data z getterů. Prakticky takovýto objekt ani nepotkáte, jelikož složí jen jakožto výplň mezi gettery a parsery (viz dále), aby mohli nějak normálně "komunikovat" - V `BakalariAPI` je `GetterOutput` hned parsován (výstup getteru je rovnou poslán do parseru) a následně už nikdy není použit.

`GetterOutput` je generická třída. Gettery totiž mohou vracet různá data a různá data potřebují různé postupy na zpracovaní. Zatím tu jsou 2 typy `GetterOutput`u - `dict` (pro JSON data) a `BeautifulSoup` (pro HTML data).

`GetterOutput` uchovává i informaci, z jakého endpointu pochází, aby mohl být vybrán správný parser.

## Parsery
"Parsery" jsou funkce, které berou `GetterOutput` a vracejí `ResultSet`. Parsery se musejí registrovat přes statický dekorátor `bakalariapi.bakalari.register_parser(Endpoint, Typ)` - musí se určit pro jaký endpoint a jaký typ `GetterOutput`u parser je. Parser vypadá nějak takto:
```py
@register_parser(Endpoint.NĚJAKÝ_ENDPOINT, dict) # Registrace parseru
def parser(getter_output: GetterOutput[dict]) -> ResultSet:
    output = ResultSet() # Příprava ResultSetu
    for zaznam in getter_output.data: # Extrakce dat z GetterOutputu
        output.add_loot(
            NějakýBakalariObject(
                zaznam["ID"],
                zaznam["nějaká_hodnota"],
            )
        )
    return output # Navrácení ResultSetu
```
Na rozdíl od getterů, parsery jsou "standardizované" a parsování se provádí s registrovanými parsery skrze funkci `bakalariapi.bakalari._parse(GetterOutput)`. Existuje i metoda `BakalariAPI._parse()`, která se chová zcela stejně, ale výsledek zároveň přidá do `Looting` instance v rámci daného `BakalariAPI`.

Může být více parserů pro jeden endpoint. Při parsování skrze `bakalariapi.bakalari._parse()` se spustí všechny parsery (které odpovídají endpointu a typu `GetterOutput`u) a jejich výsledky se sloučí. Pokud parser není schopen data parsovat, může navrátit `None` (nebo prázdný `ResultSet`, který tedy při slučování nebude mít žádný efekt).

## ResultSet
`ResultSet` je taková "malá looting instance" - shromažďuje parsované objekty, které si pak může někdo vyžádat a i metody fungují jako u `Looting` třídy. Z toho důvodu se pravděpodobně sloučení s `Looting` třídou.

## Resolvery
"Resolvery" jsou poslední v kategorii "Získání a zpracovaní dat". Jelikož Bakaláři mají často v oblibě dávat jen částečné informace, tak musí existovat funkce, které dokážou tyto informace vzít a získat kompletní informace. Například tohle potřebujeme u schůzek, kdy jsme schopni získat seznam ID schůzek a potřebujeme získat k těmto ID informace o schůzkách.

"Resolvery" jsou funkce, které berou `UnresolvedID` (= speciální generický objekt, který mohou vytvořit parsery pro tyto případy) (+ resolvery ještě berou instanci `BakalariAPI`, aby mohli dělat requesty) a vrací nějaký `BakalariObject`. Stejně jako parsery, resolvery se musí registrovat přes statický dekorátor `bakalariapi.bakalari.register_resolver(Typ)`. Resolver tedy může vypadat nějak takto:
```py
@register_resolver(NějakýBakalariObject) # Registrace resolveru
def resolver(api: BakalariAPI, unresolved: UnresolvedID) -> NějakýBakalariObject:
    with api.session_manager.get_session_or_create(RequestsSession) as session: # Získání sessionu
        data = session.get(api.get_endpoint(Endpoint.ENDPOINT_ZE_KTERÉHO_ZÍKÁVÁME_DATA_PRO_ID + "/" + unresolved.ID)).json() # Request a dekódování JSON data
    return NějakýBakalariObject( # Výstup
        data["ID"],
        data["nějaká_hodnota"],
    )
```
Jak je vidět, resolver je takové spojení getteru a parseru dohromady. Proto se v modulech většinou udělá samostatný getter a samostatný parser a resolver je jen spojuje:
```py
@register_resolver(NějakýBakalariObject)
def resolver(api: BakalariAPI, unresolved: UnresolvedID[NějakýBakalariObject]) -> NějakýBakalariObject:
    return parser_resolve(getter_resolve(api, unresolved.ID)).retrieve_type(NějakýBakalariObject)[0] # .retrive_type vrací list i když má pouze jeden objekt
```
To má i tu výhodu, že pokud někdo chce používat low-level věci, tak může používat `getter_resolve` a `parser_resolve` samostatně. Navíc parser lze zaregistrovat jako parser a tím pádem zajistit získávání více dat.

Stejně tak jako parsování, resolvování má vlastní funkci a probíhá skrze `bakalariapi.bakalari._resolve()`. A opět existuje i metoda `BakalariAPI._resolve()`, která se liší tím, že výsledek přidává do `Looting` instance, která je v daném `BakalariAPI`.

Lze mít více resolverů pro daný typ. Resolver má totiž dovoleno vrátit `None` a tím indikovat, že neuspěl, podobně jako to můžou udělat parsery. Pokud je více resolverů pro daný typ `UnresolvedID`, při resolvování se zkouší resolvery postupně v pořadí takovém, v jakém byli zaregistrovány (což značně komplikuje situace, kdy někdo by mohl chtít udělat custom resolvery na typy, které již `BakalářiAPI` resolvovat umí (jelikož resolvery z `BakalářiAPI` se zaregistrují dřív než ostatní), ale tato situace snad nenastane). Pokud nějaký resolver vrátí objekt (tedy nevrátí `None`), další resolvery se již nespustí.

# Moduly
Moduly jsou skripty, které definují gettery, parsery, resolvery nebo třeba i nějaké speciálnější funkce, které získávají/zpracovávají data. Všechny moduly jsou ve složce `modules/`. V podstatě to jsou jen skripty definující set funkcí - nemají strukturu, nemusí derivovat z nějaké dané třídy, nemusí se nikde "registrovat", nemusí prostě nic. S trochou úprav by mělo `BakalářiAPI` fungovat i pokud by se všechny moduly odebraly.

## Historie
U getterů už bylo zmíněno něco málo o modulech, ale zde to napíši znovu - Moduly původně byly zamýšleny jinak. Původně byla idea o modulech, které se budou registrovat do `BakalariAPI` třídy přes metodu nebo dekorátor (stejně jako to mají parsery nebo resolvery). Toto ale bohužel nebylo nakonec realizovatelné, protože já osobně chci mít podporu typování a to vzhledem k obrovské variaci parametrů pro různé funkce (hlavně gettery) nebylo/není proveditelné. Další iterace této ideji byla "registrace" jednotlivých funkcí modulů přes `setattr(BakalariAPI, funkce.__name__, funkce)`. Problém typování byl vyřešen jen z části - Sice se teď mohly registrovat všechny funkce bez nutnosti řešit jejich parametry/návratovou hodnotu, ale bohužel IDE nedokáže (zatím) "pochopit" `setattr()` a ve výsledku byl stav horší, jelikož tím, že tyhle funkce vlastně pro IDE neexistují a tak to akorát mělo za výsledek hromadu chybových hlášek o neexistující funkci. To bylo částečně vyřešeno vytvořením menšího Python skriptíku (`__ModuleMethodsExtractor.py`, který ale v repozitáři nikde není), který pročetl všechny moduly (pro tuto iteraci se obnovil nápad dekorátorů, na základě kterých skript poznal, že modul tuto funkci "exportuje") a vytvořil definice pro `BakalariAPI` třídu, které byly následně do překopírovány `BakalariAPI` a tím pádem IDE vědělo o existenci funkcí. V tomto momentu to bylo prakticky vyřešeno. Toto řešení ale rozbíjelo myšlenku dynamických modulů (tedy že se v této verzi musel vždy tento skript spustit a musela se upravit třída `BakalariAPI`). Tudíž se v tuto chvíli ~~zabila~~ odložila myšlenka dynamických modulů a byl přijat fakt, že se holt bude muset vždy upravit `BakalariAPI`. S tímto postavením odpadla i nutnost nějak registrovat jednotlivé funkce a tím pádem přibyla možnost funkce modulů ("manuálně") volat přímo z funkcí `BakalariAPI`. A to je stav, kde to je teď.

Osobně mě dost mrzí, že se nepřišlo na způsob, jak dynamické moduly zprovoznit (zlatý C# s možností doplňkových metod). Je dost pravděpodobné, že zde ještě někdy bude pokus o dynamické moduly (a tím pádem rewrite všech modulů PepeLaugh TeaTime), ale v blízké době to nejspíše nebude.
