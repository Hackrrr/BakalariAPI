# Úvod
Tato složka by měla poskytnout dokumentaci ohledně BakalářiAPI - jak s ním pracovat, jak funguje, nějaké termíny, které se (nejen) interně používají, či případně jak si ho upravit.

# Základ
Celý `BakalářiAPI` se točí kolem třídy `bakalari.BakalariAPI`:
```py
from bakalari import BakalariAPI
api = BakalariAPI("https://bakalari.mojeskola.cz", "MojeSkvěléJméno", "MojeSuperTajnéHeslo")
if api.is_server_running() and api.is_login_valid():
    api.init()
else:
    raise Exception("Něco se pokazilo... Sadge")
```
A violá! Je hotovo! Počkat co? Takhle ti to nestačí? No tak já jdu napsat ještě další dokumentaci...

## Sessiony
Pokud si věříš, tak nemusíš ani volat metody `.is_server_running()` a `.is_login_valid()`, ale reálně volání těchto metod tě prakticky nezpomalí jelikož je zde implementován session manager, který zužitkuje i již vytvořené sessiony. (Tady trochu lžu, jelikož `.is_server_running()` actually session manager nevyužívá.) (BTW `.init()` taky volat nemusíš, ale budou chybět některé informace, které budeš chtít a budeš dlouhou dobu hledat, proč vlastně nejsou :).)

Téměř všechny funkce potřebují udělat nějaký request na Bakaláře a je blbost, aby se pokaždé vytvořil nový session, kde by se pokaždé muselo autentizovat/přihlásit. V minulých verzích to bylo řešeno tak, že byl jeden interní session v instanci `BakalariAPI`, přes který se tyto požadavky vykonávaly. To mělo 2 hlavní nevýhody - první byla ta, že tento session byl udělán přes `requests` modul a v `BakalářiAPI` je potřeba mít i "Selenium session", který je nenahraditelný (to se vyřešilo tím, že bylo ponecháno na externím kódu, aby vždy passoval i validní Selenium session) a druhá byla ta, že je zde požadavek multitaskingu, a proto jeden session nestačí. Z toho důvodu vznikl `SessionManager`, který spravuje všechny sessiony (které se mu předají do správy) a vytváří nové "on-demand". Tím se řeší oba problémy, které zde byly při použití jednoho sessionu - Prnví je vyřešen tím, že je více druhů sessionů a při vyžádání sessionu od `SessionManager` se určuje i typ sessionu a druhý je řešen tak, že jich `SessionMannger` může mít pod správou prakticky nekonečno a navíc má Lock sekce, které zabraňují race condition problémům.

Bylo zmíněno, že máme 2 typy sessionů - `RequestsSession`, který je implementován přes `requests` modul a `SeleniumSession`, který využívá Selenia (ještě se uvažuje nad tím, že bude v `SeleniumSession` interní `RequestsSession`, který bude využíván na tasky, kde není nutné přímo Selenium a tím by se určité věci urychlili.)

Nyní tedy možná chápeš, proč tě volání metod `.is_server_running()` a `.is_login_valid()` ani moc nezpomal- teda... `.is_server_running()` tě zpomalí trochu, `.is_login_valid()` vůbec, jelikož se validní login ověřuje přihlášením a pokud je login správný, tak se při dalším požadavku již nemusí vytvářet a autentizovat session.

To byla trochu teorie o sessionech, nyní se pojďme podívat na samotné `BakalariAPI`...

## BakalariAPI
Možná čekáš, že tady toho bude nejvíc, ale reálně já tady nemám co napsat, jelikož se to dá rychle shrnout a pravděpodobně se to bude ještě měnit.

Prakticky vše, co potřebuješ vědět, je to, že existují metody `.get_fresh_NĚCO()`, případně `.get_fresh_NĚCO_NĚJAK()`... No a tyhle metody dělají to co říkají - získají "čerstvá" data/"čerstvé" dané objekty ("čerstvé" znamená, že jsou nově získána i když třeba jsou v Lootingu). (Ano, ano, vím - špatná dokumentace, někdy to ještě musím přepsat LULW). Dále jsou zde již metody `.is_server_running()` a `.is_login_valid()`, které ověřují stav serveru a zda je login správný.