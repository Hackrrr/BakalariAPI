# Changelog
Všechny důležité změny v tomto projektu budou zdokumentovány v tomto souboru.

Formát je založen na [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) a podléhá [Sémantickému verzování](https://semver.org/spec/v2.0.0.html).

## [4.0.0] - Unreleased

### Added
- Přidána možnost "inliningu" při komplexní serializaci (defaultně) - Reference, které odkazují na objekt, který je referencován pouze touto referencí se při "inliningu" nahradí referencovaným objektem; více informací v [dokumentu o serializaci](/Dokumentace/BakalariAPI/serializace.md#Inlining).
- `bakalarishell` nyní automaticky importuje předešlá data; Lze vypnout novým parametrem `--no-import`
- `bakalarishell` nyní automaticky exportuje data při vypnutí; Lze vypnout novým parametrem `-n/--no-export` u příkazu `exit`
- `bakalarishell` nyní po zapnutí vypíše obecné shrnutí

### Changed
- Změněna struktura komplexní serializace - Nyní je v `"data"` sekci komplexní serializace pouze list, root se nachází na poslední pozici v tomto listu
- Atribut `serialization.Upgradeable._atributes` změněn na `serialization.Upgradeable.deserialization_keys`
- Serializace se nyní chová k `list` a `dict` instancím stejně jako k jiným objektům, tzn. vytváření referencí na tyto instance
- Lepší porovnávání podporované verze Bakalářů a hranice zvýšena na "1.45"
- `bakalarishell` nyní všechny soubory vytváří s utf-8 kódováním; Tohle je drastická změna a bohužel může nastat situace, kdy nastane `UnicodeDecodeError` při importu starých dat. V tom případě je potřeba manuálně změnit kódování starých souborů na utf-8.
- `bakalarishell` nyní používá progress bary z `rich` modulu
- Autorun obdržel několik vylepšení a je nyní ve výchozím stavu zapnut
- Uložená konfigurace nyní neobsahuje hodnoty, které byly automaticky doplněny
- Různé další vylepšení `bakalarishell`u

### Removed
- Odtraněn parametr `-n` (alias parametru `--no-init`), jelikož `--no-*` parametrů je již více a již to zavání nedorozuměním

### Fixed
- Opravena serializace `list` instancí
- Opraven `SeleniumHandler`
- Opraven bug při spouštění `bakalarishell`, pokud nebyla vytvořena konfigurace

### Deprecated
- Data, která byla serilizována starší verzí, nebudou v dalších verzích podporována - aby data byla aktualizována na novou verzi, je potřeba je načíst a opětovně uložit

## [3.1.1] - 19. 9. 2021

### Fixed
- Oprava instalace z PyPI

## [3.1.0] - 19. 9. 2021

### Added
- Přidána možnost instalace z PyPI (`pip install bakalariapi`)
- Přidán protokol `bakalariapi.serialization.Upgradeable`, pomocí kterého mohou třídy při deserializaci převést data ze své staré struktury na novou
- Přidána možnost vytvořit `bakalarishell.shell.Shell` instanci jako "dummy shell" - takováto instance nevytváří interaktivní elementy, není možné na ní volat `.start_loop()` (jinak nastane nový exception `bakalarishell.shell.DummyShellError`) a prakticky je ji možné využít pouze jako "dispatch" ovládaný přes metodu `.proc_string`. Pokud je při spouštění shellu přítomný argument "-c exit", shell se spustí v tomto "dummy" módu (vhodné pro testování).
- Přidány metody `looting.Looting.export_data()` a `looting.Looting.import_data()`
- Přidána metoda `looting.Looting.have_id()`, která zkontroluje, zda je již objekt (daného typu a s daným ID) uložen
- Přidána metoda `objects.BakalariObject.merge()` (zatím není pořádně využitá)

### Changed
- Modul `bakalariapi.serialization` nyní řeší escapování speciálních klíčů, které používá, takže se tato věc nemusí řešit externě; Bohužel tohle může mít za následek, že stará data mohou být špatně deserializována (pokud klíč slovníku začíná hashtagem).
- Při přidávání dat do `Looting` instance se nyní data spojí se starými (tzn. import nepřepíše stará data a `.add_loot()` se pokusí stará data obohatit o nová, pokud daný objekt (resp. jeho stará verze) je už uložen)

### Fixed
- Opravena chyba při spouštění `bakalarishell` s `-c`/`--command` argumentem
- Zamezen výskyt `MarkupResemblesLocatorWarning`u z `bs4`

### Deprecated
- Metody `looting.Looting.export_json()` a `looting.Looting.import_json()` jsou nyní zastaralé, lze je nahradit skrze metody `looting.Looting.export_data()` a `looting.Looting.import_data()`, které ovšem generují serializovatelná data namísto JSONu

## [3.0.0] - 31. 8. 2021

Další major verze je tu! Kompletní (alespoň doufám) seznam změn je níže, ale pokud chceš vědět jen hlavní věci, tak tady máš souhrn:
- **`bakalariapi`**
  - Partial init mód - Nyní lze vytvořit `BakalariAPI` instanci bez parametrů a posléze s ní operovat. Takže nyní se nikdo nemusí zabývat nějakým "nastavovánín" `BakalariAPI` jen proto, aby mohl udělat `.looting.import_json()` a `.get_komens(GetMode.CACHED)`.
  - Sessiony jako kontextový manažeři - Automatické obstarání `busy` flagy při použití `with session as s: ...`.
  - Serializace - Nový přístup k serializaci přes registraci serializérů a nový formát serializace, který podporuje reference na jeden objekt z více míst (`serialization.complex_serialize()`)
- **`bakalarishell`**
  - Globální uložení konfigurace - Už není nutnost pokaždé psát parametry aby se spustil shell. Stačí pouze jednou a konfiguraci ve spuštěném shellu následně uložit `"config save"` a příště se automaticky načte tato konfigurace. S tím také přichází nová flaga `-d`, která deaktivuje načtení této konfigurace.
  - "Multi-command" podpora - Nyní lze napsat více příkazů najednou, např. `"komens;schuzky"`. Spolu s tímto je zde nový parametr `-c "příkaz"`, který spustí daný příkaz po startu shellu.
  - Barvičky

### Added
- Přidána podpora kontextový manažerů pro sessiony - pokud se session použije jakožto kontextový manažer (`with` keyword), automaticky se při vnoření do kontextru nastaví `busy` flag a při opuštění kontextu se vymaže
- Vytvořena funkce `bakalari.is_version_supported()` a metoda `BakalariAPI.is_version_supported()`, které kontrolují, zda je daná verze Bakalářů podporována
- Přidána výjimka `PartialInitError`
- Přidána závislost na balíček `appdirs` pro `bakalarishell`
- Přidán příkaz "config" do `bakalarishell`, který umožňuje práci s konfigurací (uložení, zobrazení, smazání)
- Přidán parametr `-d`/`--disable-config` pro `bakalarishell`, který zakazuje import uložené konfigurace
- Přidán parametr `-c`/`--command` pro `bakalarishell`, kterým lze spustit příkazy po startu
- Nový submodul `serialization`, který obsahuje všechny věci ohledně (de)serializace
- Přidána možnost regitrovat (de)serializéry pro typy, které nemají vlastní implementaci serializace
- Vytvořen nový formát serializace - serializovat pomocí něj lze skrze `serialization.complex_serialize()`

### Changed
- Definice `JSONEncoder` a `JSONDecoder` byly přesunuty z modulu `looting.Looting` do modulu `utils` a přejmenovány na `JSONSerializer` a `JSONDeserializer` a přesunuta a přejmenována i `logger` instance (z `bakalariapi.looting.serializer` na `bakalariapi.utils.serializer`)
- Přidán nepovinný parametr `rich_colors` (defaultně `False`) u abstraktní třídy `objects.BakalariObject`, který všechny derivující třídy implementují a který indikuje, zda ve výsledném textu mají být přítomny "tagy" na barvy (pro `rich` modul)
- `bakalarishell` nyní nevyžaduje žádné parametry při spouštění - pokud potřebný argument (url/jméno/heslo) není specifikován při startu, uživatel bude dotázán za běhu
- `BakalariAPI` lze nyní inicializovat i bez parametrů (resp. s parametry s hodnotou `None`) - v tom případě bude instance v "partial init" režimu, během kterého bude možno prověst jen určité akce, které nevyžadují k funkčnosti server (např. práce s uloženými daty); Pokud v tomto režimu bude vyžádána akce, kterou v tomto režimu provést nelze, vyvolá se výjimka `PartialInitError`
- Příkazy "export"/"import" v `bakalarishell`u nyní přijímají nepovinný poziční parametr "ID", který specifikuje ID/jméno exportovaných/importovaných dat
- Nyní je v `bakalarishell` plno barviček
- `bakalarishell` nyní podporuje více příkazů v jednom oddělených pomocí ";"
- `bakalarishell.shell.Shell` nyní parsuje příkaz pomocí `shlex` namísto vlastního regexu
- Parametry `globals_` a `locals_` u `bakalarishell.shell.pyhton_exec` jsou nyní povinné

### Removed
- Odstraněn "přímý" export `bakalariapi.LAST_SUPPORTED_VERSION`, jelikož již není potřeba pro běžné užití (avšak stále je přístupný skrz `bakalariapi.bakalari.LAST_SUPPORTED_VERSION`)
- Odstraněn parametr `-f`/`--file` pro `bakalarishell`, jelikož po zprovoznění nového systému importu/exportu již není za potřebý
- Odstraněny třídy `JSONEncoder` a `JSONDecoder`, jejich funkcionalita byla nahrazena `serialization` modulem

### Fixed
- Opravany údaje o verzi v instalační konfiguraci a v `bakalariapi`
- Opraven příkaz "test" v `bakalarishell`
- Opravena deserializace offset-aware datetime instancí (časové údaje v `objects.Meeting`)
- Konečně správný zápis typehintigu pro třídu `BakalariAPI` (za pomoci `typing.Literal`)
- Opraveny defaultní mutující hodnoty

### Deprecated
- Data, která byla serilizována staršími verzemi nebudou v další verzích podporována - stará data nutno deserializovat a opětovně serializovat (stará verze se detekuje automaticky)

## [2.1.0] - 2021-06-26

### Added
- Přidána výjimka `bakalariapi.exceptions.BakalariMissingSeleniumHandlerError`, která nastane při použití funkce vyžadující Selenium, přičemž ale nastavení Selenia nebylo poskytnuto
- Přidán parametr "command_exception_traceback_locals" u konstruktoru `bakalarishell.shell.Shell`, který specifikuje, zda se mají vypisovat proměnné (default `False`)
- Přidány docstringy a dokumentace

### Changed
- Upraven top-level export z `bakalariapi` - Nově se exportuje `GetMode` a přestal se exportovat type alias `BakalariObj`
- Přejmenovány metody `Looting.import_JSON()` a `Looting.export_JSON()` na `Looting.import_json()` a `Looting.export_json()`
- Přejmenován parametr u parametr "\_type" na "type\_" metod `ResultSet.get()` a `ResultSet.remove()` (jak doporučuje PEP 8)
- Přejmenován parametr "id" na "ID" u konstruktoru třídy `MeetingProvider`, aby se nepřepisovala builtin funkce `id()`
- Přejmenován atribut `Meeting.joinURL` na `Meeting.join_url`

### Fixed
- Logging cally nyní správně používají lazy string evaluation

## [2.0.0] - 2021-06-16

Hooooooodně velký posun od posledního (většího) updatu. Ať už v kódu, tak v organizaci a distribuci. Nejdřív něco k organizaci... Pokud tohle čteš, tak sis pravděpodobně všiml(a), že tu je tento soubor. Ano! Je tu changelog! A dokonce se drží (resp. pokouší se držet) nějakých standardů, takže tenhle projekt pravděpodobně bude mít nějakou budoucnost. Dále se přeskupily soubory. "Proč?", ptáš se cizinče? Nuže... Souvisí to s tím, že se vylepšila distribuce. Nyní stačí jen napsat `pip install git+https://github.com/Hackrrr/BakalariAPI` a voilà - Máme přímo instalovaný `bakalariapi` modul, který můžeme referencovat z jakéhokoli Python skriptu odkudkoli. A jak tohle souvisí s tím, že se přeskupily soubory? No... jelikož se projekt rozdělil i do druhého balíčku `bakalarishell` (o tom jsem se rozepsal v dokumentaci), tak je byla potřeba to trochu přeorganizovat - jak pro mě, tak i pro `setup.cfg`, který se stará o instalaci. A nakonec v rámci organizace projektu bylo provedeno i pár změn v rámci GitHubu, které nejsou pro projekt jako takový podstatný (jakožto třeba releasy nebo dependecies).

A nyní bych rád tady udělal nějaký pořádný changelog, ale vzhledem k enormnímu počtu změn to nejspíše nebude možný. Rovnou zmíním, že zde nebude vše, protože nevím, co vše se od posledního updatu změnilo. Navíc určité věci (třeba `shell.py`) byly kompletně přesány, takže rozhodně nebudu psát, co vše se zde změnilo. Spíše tedy zde napoprvé bude spíše jen takový stručný soupis změn.

### Added
- Přidána závislost na `prompt-toolkit` a `rich`
#### `bakalariapi`
- `SeleniumSession` nyní může využít `requests` modul k akceleraci určitých věcí
- `SessionManager` nyní může automaticky udržovat sessiony při životě
#### `bakalarishell`
- Přidány progress bary
- Zprovozněna nabídka příkazů z historie
- Zprovozněn hinting příkazů
- Přidána možnost `--no-init`/`-n` pro rychlejší spouštění
- Přidán příkaz `init`
- Přidány příkazy `export` a `import`
- Přidána možnost `--file`/`-f` pro specifikování I/O souboru při startu
- Přidán pěkný barevný traceback při erroru
### Changed
#### `bakalariapi`
- Implementace metod `BakalariAPI._parse()` a `BakalariAPI._resolve()` je nyní přesunuta do samostatných funkcí a byly vytvořeny stejnojmenné metody, které těchto funkcí využívají

  Není tudíž potřeba vytvářet `BakalariAPI` instanci jen kvůli parsování/resolvování)
- Metody `get_NĚCO_NĚJAK()` nyní jsou implementovány pomoci `GetMod`ů (viz dokumentace)

  Přestože to pravděpodobně bude mít určité problémy s IDE hintingem, tak si myslím, že to je poměrně dobré řešení, jelikož se značně zredukoval počet metod na `BakalariAPI` (v privátní "draftu" zde bylo asi 40 variant jen `get_NĚCO()` metod)
### Removed
- Odstaněna možnost provozu `bakalariapi` bez nainstalovaného Selenia
### Fixed
- Opravena chybná logika při špatném přihlášení
- Opravena deserializace
