# Dokumentace/Poznámky
Zde (ve složce) by mělo být vše, co není kód (ale ten se tu taky místy vyskytuje). Od toho, co `BakalářiAPI` potřebuje ke spuštění až po to, jaký funguje se vracejí z `komens` enpoint. Pokud tě zajímají ty enpointy a Bakaláři samotný (jak fungujou a jak z nich dostaneme data co chceme), tak se podívej do složkdy `Bakaláři`.

# Status
Zatím toho tady moc není, ale teď toho víc psát nehodlám... Píšu to už čtvrtím dnem a už taky trochu šílím :) . Zatím je zdokumentováno následující:
- Co `BakalářiAPI` používá a proč
- Kompletně enpointy, které `BakalářiAPI` používá (kromě domácích úkolů, ale pokud tomu rozumíš, tak si myslím, že to pochopíš)
- A to je vše... Nic moc, že? Ale věř mi - napsat to byl pain LUL

# Zprovozoznění a instalce aneb Co `BakalářiAPI` používajá a proč to potřebují?

## TL;DR
Nechceš to vše číst? V pořádku, já taky často nečtu tu hromadu nepodstatných věcí jako například takhle dlouhá a nesmyslná věta, která actually nemá žádnej význam jelikož molekuly jsou vyrobené z kamene... Anyways - potřebujeme nainstalovat `requests` a `bs4`, tedy napiš do příkazového řádku/terminálu toto:
```
pip install requests bs4
```
Ale počítej s tím, že pár věcí nebude fungovat (například získání úkolů)...

## Requests
`Requests` je balíček obsahující základní metody pro (webové) requesty - pro `BakalářiAPI` to jsou hlavně metody GET a POST. Navíc je zde možnost vytvořit sessiony - to znamená, že se za nás stará například o cookies. Pokud máte zkušenosti s `urllib3` či `urllib2`, tak tohle by měl být takový wraper kolem těchto knihoven. (Nebo alternativa k `httplib3`/`httplib2`.)
### Instalace
Balíček `Requests` je dostupný přes `pip`:
```
pip install requests
```
### Informace
- [Oficiální dokumentace](https://requests.readthedocs.io/en/master/) - User-friendly ale není tak technická, jak by mohla/měla. Obsahuje spíš příklady než popis metod.


## BeatifulSoup4 / bs4
`BeautifulSoup4` (zkráceně `bs4`) je "parser" pro HTML a XML. Pomocí něj dokážeme vytáhnout ze získaného HTML to co chceme. Dokáže i HTML/XML upravovat, ale tato/tyto funkce v `BakalářiAPI` použity nejsou. Ještě by bylo asi vhodné zmínit samotné parsery v `bs4`... Jak jsem zmiňoval, tak dokáže parsovat jak HTML tak i XML a proto musíme specifikovat správný parser - a dokonce je jich několik (pro HMTL) (viz `bs4` dokumentace). `BakalářiAPI` používá základní pro HTML, tedy `html.parser`. Alternativa je parser `html5lib` či `lxml`, které by měly být rychlejší než parser `html.parser`, ale pro ně se musejí doinstalovávat ještě další balíčky, tudíž (alespoň zatím) použity nejsou.
### Instalace
Balíček `BeautifulSoup4` je dostupný přes `pip`:
```
pip install bs4
```
Pokud chcete používat pro HTML parser `html5lib`, tak je nutnost doistalovat i balíček `html5lib`, pro parser `lxml` zase balíček `lxml` (nečekaně):
```
pip install html5lib
pip install lxml
```
### Informace
- [Oficiální dokumentace](https://www.crummy.com/software/BeautifulSoup/bs4/doc/) - Sice moc pěkná není, ale je **úplná** dokumentace, tak jak by (podle mě) měla dokumentace vypadat - Všechny metody, classy, poznámky, technický věci, ukázky ... Doporučuji alespoň si pročíst, jaký můžeme použít metody.
- [Tutoriál](https://realpython.com/beautiful-soup-web-scraper-python/) - Dokumentace je spíš na Technický věci, kokrétní metody, ... Ale pokud tohle má být první pohled na `bs4`, tak doporučuji toto - ukázka reálného využití s popisem.


## Selenium
Bakaláři jsou Bakaláři... Proto jsem musel šáhnout po absolutním overkillu - technologie (/standart) WebDriver.
#### WebDriver
WebDriver je technologie, která umožňuje ovládat vzdáleně prohlížeč - přechod mezi stránkama, klikni sem, napiš tohle, najdi toto, vytiskni stránku, ... Samozřjmě že vzdálený znamená i lokální. WebDriver se ovládá přes HTTP requesty - při spuštění se zapne na zařízení rádoby HTTP server, na který dotazy/příkazy směřují. WebDriver je většinou další program, který "obsluhuje" určitý prohlížeč. A zde je první problém - každý má používá jiný prohlížeč. Sice WebDriver je standartizovaný, ale prohlížeče ne - a proto každý prohlížeč má jiný WebDriver. A toto jaksi narušuje koncept toho, aby `BakalářiAPI` bylo pro všechny a všude fungovalo. `BakalářiAPI` sice mohou jet v "režimu" bez WebDriveru, ale určité funkce nebudou dostupné. Ještě nutno dodat, že WebDriver program se musí (většinou) stahovat zvlášť a manuálně (nestahuje se spolu se samotným prohlížečem) (tady si ale nejsem úplně jistý - prohlížeče už většinou obsahují webdriver zabudovaný, tudíž upřímně plně nechápu, proč je potřeba stahovat ještě separátní program). 
#### Selenium samotné
Teď když máme takovej malej overview toho, co je to WebDriver, přejdeme k tomu, co je `Selenium`. `Selenium` je wraper, který nám umožňuje "normálně" ovládat WebDriver přes Python (a nej pro Python - `Selenium` balíčky jsou i v JS (Node.js), C#, Java, ...). (Fun fact: `Selenium` tu bylo ještě před WebDriverem - prohlížeče tak nějak podporovaly vzdálené řízení, ale nebylo to standartizované. A pak se w3c rozhodlo toto standartizovat a tento standart vychází právě ze `Selenia`.) Nemusíme tedy řešit, jak se zapíná WebDriver pro každý prohlížeč (ale pořád musíme vědět, jak prohlížeč chceme používat a kde se nachází WebDriver program). Navíc nám poskytuje metody navíc, které nejsou v samotném standartu WebDriveru (protože WebDriver standart obsahuje pouze "atomické" příkazy).
#### Proč tohle potřebujeme?
Jak jsem psal na začátku - Bakaláři jsou Bakaláři... A používají přechno co našli. A bohužel používají i ASP.NET formy... pepeHands Ptáte se, co je to ASP.NET forma? Nůže - ASP.NET formy jsou formy, kdy se na stranu serveru posílá stav všech (interaktivních) prvků - Inputy, tlačítka, posuvníky, pozice určitých elementů, něktré texty, ... A ten request, který se následně posílá je doslova hnus (nehledě na to, že většina těch věcí se nepoužívá). Ano... Dá se to nasimulovat - Přečíst všechny hodnoty všeho, nějak to seskládat a poslat request... Ale to opravdu dělat nechci. Jen se podívejte na request, který se provede, když přepnete stránku v úkolech a pak si myslím, že od toho taky odpustíte (a to jsem člověk, který tyhle výzvy klidně podstoupí, ale tohle je už moc (jakože nejspíš bych to nějak napsal, kdyby tu nebyla možnost WebDriveru a `Selenia`)). Jak tento problém řeší použití `Selenia`? Tak, že mi se vlastně přes `Selenium` tváříme jako uživatel (který vše dělá nejvyšší (ne)možnou rychlostí) a běží nám i JavaScript. A hodnoty pro ASP.NET formy jsou generovaný přes JS, takže můžeme "jen" "kliknout" na tlačítko a z výsledku vytáhnout to co chceme (přes `BeautifulSoup4`).
#### Kdy tohle potřebujeme? Tedy co nemůžu udělat přes `BakalářiAPI` bez Selenia?
Zatím, co jsem se koukal, tak úkoly a dokumenty.
### Instalace
Opět - Balíček `Selenium` je dostupný přes `pip`:
```
pip install selenium
```
Ovšem ještě je potřeba WebDriver... Kde WebDriver pro svůj prohlížeč najít/stáhnout? Netuším... eShrug Ale nejspíše ti bude stačit vyhledat něco jako `*TVŮJ_PROHLÍŽEČ* webdriver` :).
### Informace:
- [Oficiální dokumentace](https://www.selenium.dev/selenium/docs/api/py/index.html) - Oficiální dokumentace... Upřímně je příšerná :) Ukáže doslova jen příklad základního použití a to je vše.
- [Neoficiální dokumentace](https://selenium-python.readthedocs.io/) - Z tohoto zjistíte mnohem víc (jelikož z oficiální nezjistíte nic). Text v titlu "better than official" nelže. Já osobně jsem na sem nakouknul jen jednou.
- Ještě zde uvedu toto - Nejvíce informací jsem dostal z prozkoumávání kódu `Selenia`. Sice jsem asi nepochytil, jak to má fungovat, ale našel jsem si (podle názvu) metody, které dělají to co potřebuji :) (tady actually pochválím oficiální dokumentaci, kde se píše "Use The Source Luke!")

## Nefuguje to! REEEEEE Hází mi to chybu! babyRage
Ok, ok, ok... Tak se zase uklidníme...


Jelikož `BakalářiAPI` bylo psáno na Python 3.9 a já velice rád experimentální (a nové) featury (a pak toho lituji... PepeLaugh ), tak je možné, že pár věcí nebude fungovat. Zatím vím jen o dvou chybách kompatibility:

### enum34
Pokud bude chyba vypadat nějak takto: `NameError: name 'Enum' is not defined`, tak pravděpodobně používaš Python starší jak 3.4 a chybí podpora enumerací. `BakalářiAPI` je používá (zatím) jen pro prohlížeče kvůli Seleniu. Fix by měl být jednoduchý - stačí nainstlovat balíček `enum34`:
```
pip install enum34
```

### future
Zde si nejsem jistý, zda se je to správné řešení, ale pokud se objevý chyba ve stylu: `TypeError: 'type' object is not subscriptable`, tak není **nejspíše** podpora anotací... Ale tento případ by podle mě už nastat neměl, protože by teoreticky měl spíše nastat toto: `ImporError: cannot import name 'annotations' from __future__` (tady jsem možná úplně mimo, takže to prosím berte s rezervou :) ). Každopádně pokud se to i tak ukáže, tak je řešení nainstalovat balíček `future`:
```
pip install future
```