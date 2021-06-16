# Changelog
Všechny důležité změny v tomto projektu budou zdokumentovány v tomto souboru.

Formát je založen na [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) a podléhá [Sémantickému verzování](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2021-06-16

Hooooooodně velký posun od posledního (většího) updatu. Ať už v kódu, tak v organizaci a distribuci. Nejdřív něco k organizaci... Pokud tohle čteš, tak sis pravděpodobně všiml(a), že tu je tento soubor. Ano! Je tu changelog! A dokonce se drží (resp. pokouší se držet) nějakých standardů, takže tenhle projekt pravděpodobně bude mít nějakou budoucnost. Dále se přeskupily soubory. "Proč?", ptáš se cizinče? Nuže... Souvisí to s tím, že se vylepšila distribuce. Nyní stačí jen napsat `pip install git+https://github.com/Hackrrr/BakalariAPI` a violá - Máme přímo instalovaný `bakalariapi` modul, který můžeme referencovat z jakéhokolli Python skriptu odkudkoli. A jak tohle souvisí s tím, že se přeskupily soubory? No... jelikož se projekt rozdělil i do druhého balíčku `bakalarishell` (o tom jsem se rozepsal v dokumentaci), tak je byla potřeba to trochu přeorganizovat - jak pro mě, tak i pro `setup.cfg`, který se stará o instalaci. A nakonec v rámci organizace projektu bylo provedeno i pár změn v rámci GitHubu, které nejsou pro projekt jako takový podstatný (jakožto třeba releasy nebo dependecies).

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