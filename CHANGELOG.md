# Changelog
Všechny důležité změny v tomto projektu budou zdokumentovány v tomto souboru.

Formát je založen na [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) a podléhá [Sémantickému verzování](https://semver.org/spec/v2.0.0.html).

## [Unreleased] ([3.0.0])

### Added
- Přidána podpora kontextový manažerů pro sessiony - pokud se session použije jakožto kontextový manažer (`with` keyword), automaticky se při vnoření do kontextru nastaví `busy` flag a při opuštění kontextu se vymaže
- Vytvořena funkce `bakalari.is_version_supported()` a metoda `BakalariAPI.is_version_supported()`, které kontrolují, zda je daná verze Bakalářů podporována
- Přidána výjimka `PartialInitError`
- Přidána závislost na balíček `appdirs` pro `bakalarishell`
- Přidán příkaz "config" do `bakalarishell`, který umožňuje práci s konfigurací (uložení, zobrazení, smazání)
- Přidán parametr `-d`/`--disable-config` pro `bakalarishell`, který zakazuje import uložené konfigurace
- Přidán parametr `-c`/`--command` pro `bakalarishell`, kterým lze spustit příkazy po startu
- Přidán parametr `rich_prompt` do `bakalarishell.shell.Shell`, kterým lze formátovat `.prompt` přes `rich` modul

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

### Fixed
- Opravany údaje o verzi v instalační konfiguraci a v `bakalariapi`
- Opraven příkaz "test" v `bakalarishell`
- Opravena deserializace offset-aware datetime instancí (časové údaje v `objects.Meeting`)
- Konečně správný zápis typehintigu pro třídu `BakalariAPI` (za pomoci `typing.Literal`)
- Opraveny defaultní mutující hodnoty

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
