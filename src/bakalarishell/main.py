from __future__ import annotations

import argparse
import asyncio
import getpass
import inspect
import json
import logging
import logging.config
import os
import threading
import time
import traceback
import warnings
import webbrowser
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import IO, TYPE_CHECKING, Any, Callable, cast

import bakalariapi
import platformdirs
import requests
import rich
from bakalariapi.utils import cs_timedelta, parseHTML
from prompt_toolkit.input import create_input
from prompt_toolkit.key_binding import KeyPress
from prompt_toolkit.keys import Keys
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import BarColumn, Progress, TaskID, TimeRemainingColumn
from rich.syntax import Syntax
from rich.traceback import install as tb_install
from urllib3.exceptions import InsecureRequestWarning

# Takový hack na to, aby `bakalarishell` šel spustit také přímo ze zdrojové složky
# Pokud se `bakalarishell` spustí jako modul (= přes `import`), tak vše proběhne v pořádku
# Pokud se ale spustí přes "python main.py" nebo "python bakalarishell" (kde "bakalarishell"
# je složka), tak relativní `import` selže ("ImportError: attempted relative import with no
# known parent package") a `shell` se naimportuje "přímo" (resp. ne relativně), což už je v pořádku.
# Pozn.: Pokud někdo dumá nad tím, proč zde tedy není jen druhá možnost, tak to je
# kvůli tomu, že ta zase pro změnu nefugnuje při importu jako modul, jelikož v tom případě
# hledá modul `shell` jako "globální" modul (ne jako "lokální" ve složce), tudíž selže.
if TYPE_CHECKING:
    from . import shell
else:
    try:
        from . import shell
    except ImportError:
        import shell

tb_install(show_locals=True)
cls = shell.cls

api: bakalariapi.BakalariAPI
shell_instance: shell.Shell
dirs = platformdirs.PlatformDirs(
    appauthor="BakalariAPI", appname="bakalarishell", roaming=True
)
CONFIG_FILE = "config.json"
TIME_FILE = "_lasttime"


@dataclass
class Args:
    url: str | None = None
    username: str | None = None
    password: str | None = None

    browser: str | None = None
    executable_path: str | None = None

    verbose: int = 0

    test: int | None = None
    auto_run: bool = False
    no_init: bool = False
    no_import: bool = False
    disable_config: bool = False

    commands: list[str] = field(default_factory=list)


args: Args


class RichTask:
    def __init__(self, progress: Progress, task_id: TaskID) -> None:
        self.progress = progress
        self.task_id = task_id

    def start(self):
        self.progress.start_task(self.task_id)

    def update(
        self,
        total: float | None = None,
        completed: float | None = None,
        advance: float | None = None,
        description: str | None = None,
        visible: bool | None = None,
        refresh: bool = False,
        **fields,
    ):
        self.progress.update(
            self.task_id,
            total=total,
            completed=completed,
            advance=advance,
            description=description,
            visible=visible,
            refresh=refresh,
            **fields,
        )

    def finish(self):
        task = self.progress.tasks[self.task_id]
        task.finished_time = 0


##################################################
#####                 FUNKCE                 #####
##################################################


def rich_print(
    *objects: Any,
    sep: str = " ",
    end: str = "\n",
    file: IO[str] | None = None,
    flush: bool = False,
    color: str | None = None,
    **kwargs,
):
    c = rich.get_console() if file is None else Console(file=file)
    if color is not None:
        # Pravděpodobně někdy bude problém, že se vše převádí na string, ale zatím to problém není, tak to neřeším eShrug
        objects = tuple(map(lambda x: f"[{color}]{x}[/{color}]", objects))
    return c.print(*objects, sep=sep, end=end, **kwargs)


def partial_init_notice():
    rich_print(
        'Tuto akci nelze vykonat, jelikož shell se nachází v omezeném módu. Pro přepnutí do online módu můžete zkusit příkaz "init".',
        color="yellow",
    )


def dialog_ano_ne(
    text: str = "", default: bool | None = None, color: str | None = None
) -> bool:
    message = f"{text} Ano/Ne{'' if default is None else (' (Ano)' if default else ' (Ne)')}: "
    while True:
        # ano/true/yes/1 / ne/false/no/0
        if color is not None:
            rich_print(message, end="", color=color)
            inpt = input()
        else:
            inpt = input(message)
        if len(inpt) == 0:
            if default is None:
                continue
            return default
        input_letter = inpt[0].lower()
        if input_letter in "aty1":
            return True
        if input_letter in "nf0":
            return False


def dialog_cislo(text: str = "", default: int | None = None):
    print(text, "" if default is None else f"({default})")
    while True:
        inpt = input()
        if not inpt:
            if default is None:
                continue
            return default
        if inpt.isdecimal():
            return int(inpt)
        print("Špatná hodnota")


def print_keys(keys: list[tuple[str, str] | str], enter_pokracovani=True):
    output = ["Enter - Pokračování"] if enter_pokracovani else []
    for key in keys:
        if isinstance(key, tuple):
            if key[1] == "":
                output.append(key[0])
            else:
                output.append(f"[{key[1]}]{key[0]}[/{key[1]}]")
        else:
            output.append(key)
    rich_print(", ".join(output))


def show(obj: bakalariapi.objects.BakalariObject, title: str | None = None):
    if title is not None:
        print(title)

    if isinstance(obj, bakalariapi.Komens):
        rich_print(obj.format(True))
        print("\n\n")
        print_keys([("P - Potrvrdí přečtení zprávy", "" if obj.confirmed else "green")])

        def komens_key_handler(key_press: KeyPress, done: Callable):
            if key_press.key == "p":
                print("Potvrzuji zprávu...")
                obj.confirm(api)
                print("Zpráva potvrzena")

        asyncio.run(keyhandler(komens_key_handler))

    elif isinstance(obj, bakalariapi.Grade):
        rich_print(obj.format(True))
        print("\n\n")

        asyncio.run(keyhandler(None))

    elif isinstance(obj, bakalariapi.Meeting):
        rich_print(obj.format(True))
        print("\n\n")

        is_before = obj.is_before_start
        delta = obj.start_time_delta
        color = ""
        # Delta totiž může být očividně i negativní
        if not is_before and delta >= timedelta(hours=-1):
            color = "red"
        elif is_before and delta <= timedelta(minutes=5):
            color = "yellow"
        elif is_before and delta <= timedelta(minutes=30):
            color = "green"

        print_keys(
            [("O - Otevře schůzku v prohlížeči", color), "Z - Zobrazí HTML pozvánky"]
        )

        def meeting_key_handler(key_press: KeyPress, done: Callable):
            key = key_press.key.lower()
            if key == "o":
                webbrowser.open(obj.join_url)
            elif key == "z":
                c = Console()
                c.print(Syntax(str(parseHTML(obj.content).prettify()), "html"))

        asyncio.run(keyhandler(meeting_key_handler))
    # elif isinstance(obj, bakalariapi.Student):
    #     pass

    elif isinstance(obj, bakalariapi.Homework):
        rich_print(obj.format(True))
        print("\n\n")

        print_keys(
            [
                ("H - Označí úkol jako hotový", "" if obj.done else "green"),
                "N - Označí úkol jako nehotový",
                "Z - Zobrazí HTML úkolu",
            ]
        )

        def homework_key_handler(key_press: KeyPress, done: Callable):
            key = key_press.key.lower()
            if key == "h":
                obj.mark_as_done(api, True)
                print("Úkol označen jako hotový")
            elif key == "n":
                obj.mark_as_done(api, False)
                print("Úkol označen jako nehotový")
            elif key == "z":
                c = Console()
                c.print(Syntax(str(parseHTML(obj.content).prettify()), "html"))

        asyncio.run(keyhandler(homework_key_handler))

    else:
        raise Exception(f"Undefined type '{type(obj)}' to show")


async def keyhandler(
    handler: Callable[[KeyPress, Callable[[], None]], None] | None,
    *,
    done_on_enter: bool = True,
    mask_keyboard_interrupt: bool = False,
):
    """
    Začne zaznamenávat zmáčklé klávesy, které následně passuje do dané funkce.

    Args:
        handler:
            Funkce do které se passují zaznamenané klávesy.
            Bere 2 argumenty:
                key_press:
                    Zaznamenaný stisk klávesy.
                done:
                    Funkce, která při zavolání ukončí záznam kláves.
            Pokud je `None`, nic se nevolá.
            Hodnota `None` má smysl pouze pokud parametr `done_on_enter` je `True`.
        done_on_enter:
            Pokud True, tak se při klávese Enter ukončí záznam kláves.
            Pozn.: Pokud True, tak se funkce v parametru handler nevolá.
        mask_keyboard_interrupt:
            Pokud `True`, tak `KeyboardInterrupt` bude potlačen.
            Pokud `False`, `KeyboardInterrupt` bude propagován.
            Pozn.: Ve skutečnosti je `KeyboardInterrupt` simulován, jelikož z asyncio loopu `KeyboardInterrupt` nepřichází.
    Příklad:
    ```
    def handler(keys_press: KeyPress, done: Callable):
        if key_press.key == "q":
            done()
    asyncio.run(keyhandler(handler))
    ```
    Nebo, pokud máme asynchoní funkci, lepší řešení pro poslední řádku je:
    ```
    await keyhandler(handler)
    ```
    """
    evnt = asyncio.Event()
    inpt = create_input()

    done = lambda: evnt.set()

    def key_handler_proc(keys: list[KeyPress]):
        for key_press in keys:
            if done_on_enter and key_press.key == Keys.Enter:
                done()
            # elif key_press.key == Keys.F4:
            #     for key_press in keys:
            #         if key_press.key == Keys.Escape:
            #             raise SystemExit
            elif not mask_keyboard_interrupt and key_press.key == Keys.ControlC:
                raise KeyboardInterrupt
            elif handler is not None:
                handler(key_press, done)

    with inpt.raw_mode():
        with inpt.attach(lambda: key_handler_proc(inpt.read_keys())):
            await evnt.wait()


def get_io_filepath(file: str) -> str:
    return os.path.join(dirs.user_data_dir, file)


def get_io_file(file: str, create_file: bool, mode: str = "r+") -> IO:
    """Vrátí file handler na daný soubor `file` v uživatelské (data) složce."""
    path = get_io_filepath(file)
    if not os.path.exists(path):
        if not create_file:
            raise FileNotFoundError()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "x", encoding="utf-8"):
            pass
    return open(path, mode, encoding="utf-8")


def save_config():
    with get_io_file(CONFIG_FILE, True) as f:
        # Indent, protože chci, aby to šlo přehledně upravit i z editoru (i když k tomu nejspíše nikdy nedojde)
        # (a navíc alespoň nemusí řešit formátování při "config show")
        json.dump(args.__dict__, f, indent=4)


def disable_ssl():
    def patch(f: Callable):
        def patched(*args, **kwargs):
            # `cast()` protože jsem zatím nepřišel na způsob, jak dostat hint při patchování metod (pomocí `ParamSpec`u)
            session = cast(bakalariapi.sessions.RequestsSession, args[0])
            bound = inspect.signature(f).bind(*args, **kwargs)
            bound.apply_defaults()
            login = bound.arguments["login"]
            bound.arguments["login"] = False
            x = f(*bound.args, **bound.kwargs)
            session.session.verify = False
            if login:
                session.login()
            return x

        return patched

    bakalariapi.sessions.RequestsSession.__init__ = patch(
        bakalariapi.sessions.RequestsSession.__init__
    )
    # Když nastavíme `verify` na `False` (v `requests` modulu), `urllib3` si začne stěžovat
    warnings.filterwarnings("ignore", category=InsecureRequestWarning)


##################################################
#####             PŘÍKAZO-FUNKCE             #####
##################################################


def Init() -> bool:
    def partial_init_mode():
        rich_print(
            "\nInicilizace neproběhla úspěšně a shell poběží v omezeném módu.\nPro přepnutí do plného módu zkuste opětovat inicializaci pomocí příkazu 'init'.",
            color="yellow",
        )

    def ask_import() -> bool:
        try:
            if args.no_import:
                if dialog_ano_ne(
                    "Server není dostupný; Chce importovat uložená data?",
                    True,
                    "yellow",
                ):
                    Command_Import()
                else:
                    partial_init_mode()
            else:
                rich_print(
                    "Server není dostupný; Uložená data byla již importována, je tedy možné pracovat se starými daty",
                    color="yellow",
                )
                partial_init_mode()
        except KeyboardInterrupt:
            partial_init_mode()
        return False

    if args.url is None:
        try:
            args.url = input("URL adresa serveru: ")
            api.server_info.url = args.url
        except KeyboardInterrupt:
            rich_print("\nNebyla zadána adresa serveru", color="red")
            partial_init_mode()
            return False
    if args.username is None:
        try:
            args.username = input("Přihlašovací jméno: ")
            api.username = args.username
        except KeyboardInterrupt:
            rich_print("\nNebylo zadáno přihlašovací jméno", color="red")
            partial_init_mode()
            return False
    if args.password is None:
        try:
            args.password = getpass.getpass("Heslo: ")
        except KeyboardInterrupt:
            rich_print(
                "\nHeslo nebylo zadáno, předpokládá se prázdné heslo", color="yellow"
            )
            args.password = ""
        api.password = args.password

    try:
        rich_print(
            f"Kontrola stavu serveru a přihlašovacích údajů pro uživatele [cyan]{api.username}[/cyan]...",
            highlight=False,
        )
        try:
            if not api.is_login_valid():
                rich_print("Přihlašovací údaje jsou neplatné", color="red")
                partial_init_mode()
                return False
        except requests.exceptions.SSLError:
            # rich.get_console().print_exception()
            try:
                if dialog_ano_ne(
                    "Nepodařilo se navázat zabezpečené připojení k serveru. Chcete pokračovat s nezabezpečeným připojením?",
                    False,
                    "yellow",
                ):
                    disable_ssl()
                    api.session_manager.kill_all(False)
                    print(
                        "Deaktivovalo se zabezpečené připojení, inicializace nyní proběhne znovu..."
                    )
                    return Init()
                else:
                    return ask_import()
            except KeyboardInterrupt:
                partial_init_mode()
                return False
        except requests.exceptions.RequestException:
            return ask_import()
    except KeyboardInterrupt:
        rich_print("Inicializace byla předčasně ukončena", color="yellow")
        partial_init_mode()
        return False
    rich_print("Server běží a přihlašovací údaje jsou správné", color="green")
    print("Nastavuji...")
    try:
        with warnings.catch_warnings():
            # Nechceme dostat `VersionMismatchWarning`, protože v `SeverInfo()` kontrolujeme verzi manuálně
            warnings.simplefilter("ignore")
            api.init()
    except KeyboardInterrupt:
        rich_print(
            "Nebyly získány informace o stavu serveru, ale žádné funkce by tímto neměli být ovlivněny",
            color="yellow",
        )
        return True
    print("Nastaveno:")
    ServerInfo()
    return True


def ServerInfo():
    rich_print(
        f"Typ uživatele: {'[bright_black]Není k dispozici[/bright_black]' if api.user_info.type == '' else f'[cyan]{api.user_info.type}[/cyan]'}\n"
        f"Uživatelký hash: {'[bright_black]Není k dispozici[/bright_black]' if api.user_info.hash == '' else f'[cyan]{api.user_info.hash}[/cyan]'}\n"
        f"Verze Bakalářů: {'[bright_black]Není k dispozici[/bright_black]' if api.server_info.version is None else f'[cyan]{api.server_info.version}[/cyan]'}\n"
        f"Datum verze Bakalářů: {'[bright_black]Není k dispozici[/bright_black]' if api.server_info.version_date is None else '[cyan]'+api.server_info.version_date.strftime('%d. %m. %Y')+'[/cyan] [bright_black]('+cs_timedelta((datetime.now() - api.server_info.version_date), 'd')+' stará verze)[/bright_black]'}\n"
        f"Evidenční číslo verze Bakalářů: {'[bright_black]Není k dispozici[/bright_black]' if api.server_info.evid_number is None else f'[cyan]{api.server_info.evid_number}[/cyan]'}\n",
        highlight=False,
    )
    if not (api.server_info.version is None) and not api.is_version_supported():
        rich_print(
            "*** Jiná verze Bakalářů! Všechny funkce nemusejí fungovat správně! ***",
            highlight=False,
            color="yellow",
        )


def Command_Komens(limit: int | None = None, force_fresh: bool = False):
    def fresh() -> list[bakalariapi.Komens]:
        if api.is_partial_init:
            partial_init_notice()
            return []
        output: list[bakalariapi.Komens] = []
        with Progress() as progress:
            task = RichTask(
                progress, progress.add_task("Získávání zpráv", start=False, total=0)
            )
            unresolved = api._parse(
                bakalariapi.modules.komens.getter_komens_ids(api)
            ).get(bakalariapi.UnresolvedID)[:limit]
            task.update(total=len(unresolved))
            for unresolved_id in unresolved:
                output.append(api._resolve(unresolved_id).get(bakalariapi.Komens)[0])
                task.update(advance=1)

        return output

    if force_fresh:
        zpravy = fresh()
    else:
        zpravy = api.get_komens(bakalariapi.GetMode.CACHED)
        if len(zpravy) == 0:
            print("Žádné zprávy v Lootingu, zkouším načíst ze serveru")
            zpravy = fresh()

    length = len(zpravy)
    if length == 0:
        print("Nebyly nalezeny žádné aktualní schůzky")
        return
    cls()
    count = 1
    for zprava in zpravy:
        try:
            show(zprava, f"*** Zpráva {count} z {length} ***")
            count += 1
            cls()
        except KeyboardInterrupt:
            print("\n")
            break


def Command_Znamky(force_fresh: bool = False):
    print("Získávám známky...")

    try:
        znamky = api.get_grades(
            bakalariapi.GetMode.FRESH
            if force_fresh
            else bakalariapi.GetMode.CACHED_OR_FRESH
        )
    except bakalariapi.exceptions.PartialInitError:
        partial_init_notice()
        return

    length = len(znamky)
    print(f"Známky získány ({length}), zobrazuji...")
    cls()
    count = 1
    for znamka in znamky:
        try:
            show(znamka, f"*** Známka {count} z {length} ***")
            count += 1
            cls()
        except KeyboardInterrupt:
            print("\n")
            break


def Command_Schuzky(force_fresh: bool = False):
    def fresh():
        if api.is_partial_init:
            partial_init_notice()
            return []
        output = []
        with Progress() as progress:
            task = RichTask(
                progress, progress.add_task("Získávání schůzek", start=False, total=0)
            )
            unresolved = api._parse(
                bakalariapi.modules.meetings.getter_future_meetings_ids(api)
            ).get(bakalariapi.UnresolvedID)
            task.update(total=len(unresolved))
            for unresolved_id in unresolved:
                output.append(api._resolve(unresolved_id).get(bakalariapi.Meeting)[0])
                task.update(advance=1)
        return output

    if force_fresh:
        schuzky = fresh()
    else:
        schuzky = api.get_meetings(bakalariapi.GetMode.CACHED)
        if len(schuzky) == 0:
            print("Žádné schůzky v Lootingu, zkouším načíst ze serveru")
            schuzky = fresh()

    length = len(schuzky)
    if length == 0:
        print("Nebyly nalezeny žádné aktualní schůzky")
        return
    cls()
    count = 1
    for schuzka in schuzky:
        try:
            show(schuzka, f"*** Schůzka {count} z {length} ***")
            count += 1
            cls()
        except KeyboardInterrupt:
            print("\n")
            break


def Command_Studenti(force_fresh: bool = False):
    print("Získávám studenty...")

    try:
        studenti = api.get_students(
            bakalariapi.GetMode.FRESH
            if force_fresh
            else bakalariapi.GetMode.CACHED_OR_FRESH
        )
    except bakalariapi.exceptions.PartialInitError:
        partial_init_notice()
        return

    length = len(studenti)
    print(f"Studenti získáni, počet studentů je {length}")
    try:
        count = dialog_cislo("Kolik zobrazit výsledků najednou?", 25)
    except KeyboardInterrupt:
        return
    offset = 0
    cls()
    while offset < length:
        try:
            for _ in range(count):
                if offset >= length:
                    break
                print(studenti[offset].format())
                offset += 1
            input(
                f"Pro pokračování stiskni klávasu... (Již zobrazeno {offset} výsledků z {length})"
            )
            cls()
        except KeyboardInterrupt:
            print("\n")
            break


def Command_Ukoly(fast: bool = False, force_fresh: bool = False):
    print("Načítání úkolů...")

    try:
        if fast:
            ukoly = api.get_homeworks(
                bakalariapi.GetMode.FRESH
                if force_fresh
                else bakalariapi.GetMode.CACHED_OR_FRESH,
                fast_mode=True,
            )
        else:
            ukoly = api.get_homeworks(
                bakalariapi.GetMode.FRESH
                if force_fresh
                else bakalariapi.GetMode.CACHED_OR_FRESH,
                fast_mode=False,
                unfinished_only=False,
                only_first_page=False,
            )
    except bakalariapi.exceptions.PartialInitError:
        partial_init_notice()
        return

    hotove = 0
    nehotove = 0
    for ukol in ukoly:
        if ukol.done:
            hotove += 1
        else:
            nehotove += 1

    if hotove + nehotove == 0:
        print("Nebyly nalezeny žádné aktualní úkoly")
        return
    print(f"Úkoly načteny (hotové {hotove}, nehotové {nehotove})")
    zobraz_hotove = fast or dialog_ano_ne("Chte zobrazit již hotové úkoly?")
    count = 1
    for ukol in ukoly:
        try:
            if not zobraz_hotove and ukol.done:
                continue
            cls()
            show(
                ukol,
                f"*** Domácí úkol {count} z {hotove + nehotove if zobraz_hotove else nehotove} ***",
            )
            count += 1
        except KeyboardInterrupt:
            print("\n")
            break


def Command_Konec(nice: bool = True):
    shell_instance.stop_loop()
    api.kill(nice)


def Command_Export(file_name: str = "main"):
    print("Generace JSON dat...")
    with get_io_file(file_name, True) as f:
        json.dump(api.looting.export_data(), f, ensure_ascii=False)
        # Odstraníme data, která jsou případně po JSONu, co jsme teď napsali (třeba pozůstatek po předchozím JSONu, pokud byl delší jak náš současný)
        f.truncate()
    print(f"JSON data vygenerována a zapsána do souboru '{file_name}'")


def Command_Import(file_name: str = "main"):
    try:
        with get_io_file(file_name, False) as f:
            api.looting.import_data(json.loads(f.read()))
    except FileNotFoundError:
        rich_print(
            f"Data nebyla načtena, jelikož soubor '{file_name}' neexistuje",
            color="yellow",
        )
    else:
        print(f"Data ze souboru '{file_name}' byla načtena")


def Command_Config(namespace: dict[str, Any]):
    cmd = namespace["cmd"]
    config_path = get_io_filepath(CONFIG_FILE)
    if cmd == "show":
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                rich_print(Syntax(f.read(), "json"))
        else:
            print("Žádná konfigurace není uložená")
    elif cmd == "save":
        save_config()
        print("Konfigurace uložena")
    elif cmd == "remove":
        if os.path.exists(config_path):
            os.remove(config_path)
            print("Konfigurace byla vymazána")
        else:
            print("Nic se nevykonalo, jelikož konfigurace není uložená")
    elif cmd == "check":
        if os.path.exists(config_path):
            s = os.stat(config_path)
            rich_print(
                f"Konfigurace je uložená z data {datetime.fromtimestamp(s.st_mtime).strftime('%d. %m. %Y, %H:%M:%S')}, velikost konfigurace je {s.st_size}B"
            )
        else:
            print("Žádná konfigurace není uložená")
    elif cmd == "open":
        dirname = os.path.dirname(config_path)  # = dirs.user_data_dir()
        if os.path.exists(dirname):
            webbrowser.open(os.path.realpath(dirname))
        else:
            print("Nelze otevřít konfigurační složku, jelikož neexistuje")


##################################################
#####                TESTY                   #####
##################################################


def RunTest(ID: int):
    m = __import__(__name__)
    t = f"Test{ID}"
    if hasattr(m, t):
        rich_print(f"Zahajuji test {ID}")
        try:
            o = getattr(m, t)()
            rich_print(
                f"Test {ID} skončil" + ("" if o is None else "; Výsledek testu:")
            )
            if o is not None:
                rich_print(o)
        except:
            rich_print("Test skončil neúspěchem:", color="red")
            traceback.print_exc()
    else:
        rich_print(f"Test {ID} nenalezen", color="red")


def Test0():
    print("Spouštím testování...")
    with api.session_manager.get_session_or_create(
        bakalariapi.sessions.RequestsSession
    ) as session:
        try:
            while True:
                last = session.get(
                    api.get_endpoint(bakalariapi.bakalari.Endpoint.SESSION_INFO)
                ).json()["data"]["remainingTime"]
                print("\r", end="")
                while True:
                    print(
                        "Současný zbývající čas: " + str(last) + " " * 20, end="\r"
                    )  # Some spaces to rewrite previous text...
                    session.get(
                        api.get_endpoint(bakalariapi.bakalari.Endpoint.SESSION_EXTEND)
                    )
                    current = float(
                        session.get(
                            api.get_endpoint(bakalariapi.bakalari.Endpoint.SESSION_INFO)
                        ).json()["data"]["remainingTime"]
                    )
                    if last < current:
                        print("\n")
                        break
                    last = current
                    time.sleep(1)
                print(
                    "Sezení bylo prodlouženo, když zbývalo "
                    + str(last)
                    + " (+ max 1s) do konce a bylo prodlouženo na "
                    + str(current)
                )
        except KeyboardInterrupt:
            print("Testování ukončeno")


def Test1():
    # "Kopírování"
    print("Vytváření kopie dat skrze export/import...")
    data = api.looting.export_data()
    new = bakalariapi.looting.Looting()
    new.import_data(data)
    print("Kopie vytvořena")

    # Porovnávání
    typ_mismatch = 0
    id_len_mismatch = 0
    id_mismatch = 0
    print("=" * 30)
    print(f"Počet typů v datech (old): {len(api.looting.data)}")
    print(f"Počet typů v datech (new): {len(api.looting.data)}")
    print("Porovnávání zahájeno...")
    for typ_old, typ_new in zip(api.looting.data.keys(), new.data.keys()):
        if typ_old != typ_new:
            print(f"Neshodující se typy! Old: '{typ_old}'; New: '{typ_new}'")
            typ_mismatch += 1
            continue
        old_id_len = len(api.looting.data[typ_old])
        new_id_len = len(new.data[typ_new])
        if old_id_len != new_id_len:
            print(
                f"Neshodující se počet záznamů pro typ {typ_old}! Old: {old_id_len}; New: {new_id_len}"
            )
            id_len_mismatch += 1
        for id_old, obj_old, id_new, obj_new in zip(
            api.looting.data[typ_old].keys(),
            api.looting.data[typ_old].values(),
            new.data[typ_new].keys(),
            new.data[typ_new].values(),
        ):
            if id_old != id_new:
                print(
                    f"Neshodující se ID! Old: '{id_old}'; New: '{id_new}' (typ: {typ_old}; ID type (old): {type(id_old)}; ID type (new): {type(id_new)})"
                )
                id_mismatch += 1

    print(
        f"Porovnávání dokončeno:\nChyb u typů:\t{typ_mismatch}\nChyb u ID:\t{id_mismatch}"
    )
    return (typ_mismatch, id_mismatch, id_len_mismatch)


def Test2():
    print("Získávám IDčka online schůzek...")
    IDs = api._parse(
        bakalariapi.modules.meetings.getter_meetings_ids(
            api, datetime(1, 1, 1), datetime(9999, 12, 31, 23, 59, 59)
        )
    ).get(bakalariapi.UnresolvedID)
    la = len(IDs)
    print(f"IDčka online schůzek získany ({la})")
    print()
    error: list[bakalariapi.UnresolvedID[bakalariapi.Meeting]] = []
    try:
        with Progress() as progress:
            task = RichTask(progress, progress.add_task("Získávání schůzek", total=la))
            for ID in IDs:
                task.update(description=f"Schůzka {ID.ID}")
                try:
                    api._resolve(ID)
                except bakalariapi.exceptions.BakalariQuerrySuccessError as e:
                    progress.log(f"Online schůzku {ID.ID} se nepodařilo načíst")
                    error.append(ID)
                finally:
                    task.update(advance=1)
    except KeyboardInterrupt:
        pass
    finally:
        le = len(error)
        print(
            f"Úspěšné pokusy: {la - le}; Neúspěšné pokusy: {le}; Chybovost: {le/la*100:.2f}%"
        )


def Test3():
    print("Tento test již není podporován... Sadge")
    return
    # return API.GetHomeworksIDs()


def Test4():
    print("Tento test již není podporován... Sadge")
    return
    # return API.MarkHomeworkAsDone(input("ID Úkolu: "), input("ID Studenta: "), True)


def Test5():
    print("Tento test již není podporován... Sadge")
    return
    # homeworks = API.GetHomeworks()
    # print("Úkoly načteny...")
    # zobrazHotove = AnoNeDialog("Chte zobrazit již hotové úkoly?")
    # cls()
    # for homework in homeworks:
    #     if not zobrazHotove and homework.Done:
    #         continue
    #     print("*** Domácí úkol ***")
    #     print(homework.Format())
    #     print("\n\n")
    #     input("Pro pokračování stiskni klávasu...")
    #     cls()


def Test6():
    count_total = 0
    count_invalid = 0
    try:
        while True:
            count_total += 1
            output = api.get_homeworks(
                bakalariapi.GetMode.FRESH,
                fast_mode=False,
                unfinished_only=False,
                only_first_page=False,
            )
            if len(output) <= 20:
                count_invalid += 1
                print("==============================")
                print(f"Nepodařil se se pokus číslo {count_total}")
                print(f"Nepodařených pokusů je {count_invalid} z {count_total}")
                probrallity = (count_total - count_invalid) / count_total * 100
                print("Pravděpodobnost úspěšnosti je %.2f%%" % probrallity)
                print("==============================")
            time.sleep(5)
    except KeyboardInterrupt:
        print("==============================")
        print(f"Nepodařených pokusů bylo {count_invalid} z celkových {count_total}")
        probrallity = (count_total - count_invalid) / count_total * 100
        print("Konečná ravděpodobnost úspěšnosti je %.2f%%" % probrallity)


##################################################
#####                MAIN                    #####
##################################################
def main():
    global api
    global args

    def load_args_from_config() -> dict | None:
        global args
        with get_io_file(CONFIG_FILE, True) as f:
            parsed = json.load(f)
        return parsed

    parser = argparse.ArgumentParser(
        description="Shell integrující funkcionalitu BakalářiAPI",
        epilog="Ano, ano, ano... Actually je to web scraper, ale API zní líp :)",
    )
    if parser.prog == "":
        parser.prog = "bakalarishell"
    parser.add_argument(
        "url",
        help="URL na bakaláře (př. https://bakalari.skola.cz); Pokud není tento argument přítomen, program se zeptá za běhu",
        nargs="?",
        default=None,
    )
    parser.add_argument(
        metavar="jmeno",
        help="Přihlašovací jméno; Pokud není tento argument přítomen, program se zeptá za běhu",
        dest="username",
        nargs="?",
        default=None,
    )
    parser.add_argument(
        metavar="heslo",
        nargs="?",
        help="Přihlašovací heslo; Pokud není tento argument přítomen, program se zeptá za běhu",
        dest="password",
        default=None,
    )
    parser.add_argument(
        "-b",
        "--browser",
        choices=[x.name.lower() for x in bakalariapi.Browser],
        type=str.lower,  # => case-insensitive
        help="Specifikuje WebDriver prohlížeče, který použít",
        default=None,
    )
    parser.add_argument(
        "-e",
        "--executablePath",
        help="Cesta ke spustitelnému webdriveru pro prohlížeč, který je specifikovaný pomocí '-b'",
        dest="executable_path",
        default=None,
    )
    parser.add_argument(
        "-t",
        "--test",
        type=int,
        help="Test, který se má spustit",
        # dest="test",
        metavar="ID",
        default=None,
    )
    parser.add_argument(
        "-a",
        "--auto-run",
        help="Pokud je tato flaga přítomna, spustí se automatické úlohy",
        action="store_true",
        dest="auto_run",
        default=None,
    )
    parser.add_argument(
        "-n",
        "--no-init",
        help="Pokud je tato flaga přítomna, nebude BakalariAPI instance automaticky inicializována",
        action="store_true",
        dest="no_init",
        default=None,
    )
    parser.add_argument(
        "--no-import",
        help="Pokud je tato flaga přítomna, nebude proveden import dat (z hlavního souboru)",
        action="store_true",
        dest="no_import",
        default=None,
    )
    parser.add_argument(
        "-v",
        "--verbose",
        help="Zapne shell v 'ukecaném módu'; Lze opakovat vícekrát pro větší 'ukecanost' (max 5)",
        action="count",
        default=None,
    )
    parser.add_argument(
        "-d",
        "--disable-config",
        help="Soubor s konfigurací se bude ignorovat, tudíž se brát v potaz pouze argumenty z příkazové řádky",
        action="store_true",
        dest="disable_config",
        default=None,
    )
    parser.add_argument(
        "-c",
        "--command",
        help="Vykoná daný příkaz po zapnutí shellu (po autorunu); Lze opakovat vícekrát",
        action="append",
        dest="commands",
        default=None,
    )
    # Všechny argumenty pro argparse MUSÍ mít "default=None", jinak se neprofiltrují
    # a nelze pro daný argument načíst hodnotu z configu (protože hodnota z configu
    # se přepíše hodnotou "None" z argparse)
    parsed = {k: v for k, v in vars(parser.parse_args()).items() if v is not None}
    # Jelikož hodnoty filtrujeme, tak pokud i po filtrování je "disable_config"
    # v "parsed" tak má hodnotu `True`, tudíž se můžeme dotazovat (jen) přes `in`
    if not ("disable_config" in parsed):
        from_config = load_args_from_config()
        if from_config is not None:
            parsed = from_config | parsed
    args = Args(**parsed)

    # Verbose:
    #   0 - Nic
    #   1 - Warning; Pouze BakalářiAPI
    #   2 - Info; Pouze BakalářiAPI
    #   3 - Debug; Pouze BakalářiAPI
    #   4 - Info
    #   5 - NOSET
    if args.verbose != 0:
        logging.basicConfig(
            level=[
                None,
                "WARNING",
                "INFO",
                "DEBUG",
                "INFO",
                "NOTSET",
            ][args.verbose],
            datefmt="[%X]",
            handlers=[RichHandler()],
        )
        logging.info(
            "Logging zapnut na levelu %s (%s)",
            args.verbose,
            logging.getLevelName(logging.root.level),
        )
        if args.verbose < 4:
            for logger in [
                logging.getLogger(name) for name in logging.root.manager.loggerDict
            ]:
                if logger.name.startswith("bakalariapi"):
                    continue
                logger.propagate = False
            # logging.getLogger("bakalariapi").propagate = True

    selenium: bakalariapi.SeleniumHandler | None = None
    if args.browser is not None:
        selenium = bakalariapi.SeleniumHandler(
            bakalariapi.Browser[args.browser.upper()],
            args.executable_path,
        )

    api = bakalariapi.BakalariAPI(args.url, args.username, args.password, selenium)

    successful_init = False
    if not args.no_init:
        successful_init = Init()

    if not args.no_import:
        try:
            with get_io_file("main", False) as f:
                api.looting.import_data(json.loads(f.read()))
        except FileNotFoundError:
            pass

    if args.test is not None:
        RunTest(args.test)

    prepare_shell()
    # Chceme `main()` locals, ne `prepare_shell()` locals
    shell_instance.PYTHON_EXEC_LOCALS = locals()

    print()

    rich_print(
        f"Bakalarishell připraven - verze BakalářiAPI je "
        + f"[green_yellow]{bakalariapi.__version__}[/green_yellow]"
        if "dev" in bakalariapi.__version__
        else f"[bright_cyan]{bakalariapi.__version__}[/bright_cyan]"
    )

    lasttime: datetime = datetime.max
    try:
        with get_io_file(TIME_FILE, False) as f:
            lasttime = datetime.fromisoformat(f.read())
    except FileNotFoundError:
        pass

    if args.auto_run:
        if successful_init:

            def task_ukoly(api: bakalariapi.BakalariAPI, task: RichTask):
                length = len(
                    api.get_homeworks(bakalariapi.GetMode.FRESH, fast_mode=True)
                )
                task.update(total=length, completed=length)

            def task_komens(api: bakalariapi.BakalariAPI, task: RichTask):
                unresolved = api._parse(
                    bakalariapi.modules.komens.getter_komens_ids(
                        api,
                        from_date=None if lasttime is None else lasttime - timedelta(5),
                    )
                ).get(bakalariapi.UnresolvedID)
                task.update(total=len(unresolved))
                task.start()
                for unresolved_id in unresolved:
                    api._resolve(unresolved_id)
                    task.update(advance=1)

            def task_znamky(api: bakalariapi.BakalariAPI, task: RichTask):
                length = len(api.get_all_grades())
                task.update(total=length, completed=length)

            def task_schuzky(api: bakalariapi.BakalariAPI, task: RichTask):
                unresolved = api._parse(
                    bakalariapi.modules.meetings.getter_future_meetings_ids(api)
                ).get(bakalariapi.UnresolvedID)
                task.update(total=len(unresolved))
                task.start()
                for unresolved_id in unresolved:
                    api._resolve(unresolved_id)
                    task.update(advance=1)

            @dataclass
            class Task:
                description: str
                function: Callable[[bakalariapi.BakalariAPI, RichTask], None]
                start: bool = True

            tasks: list[Task] = [
                Task("Získání Komens zpráv", task_komens, False),
                Task("Získání schůzek", task_schuzky, False),
                Task("Získání úkolů", task_ukoly),
                Task("Získání známek", task_znamky),
            ]

            def autorun():
                with Progress(
                    "[progress.description]{task.description}",
                    BarColumn(),
                    "[progress.percentage]{task.percentage:>3.0f}%",
                    "{task.completed}/{task.total}",
                    TimeRemainingColumn(),
                ) as progress:
                    threads: list[threading.Thread] = []
                    for task in tasks:
                        thread = threading.Thread(
                            target=task.function,
                            args=(
                                api,
                                RichTask(
                                    progress,
                                    progress.add_task(
                                        task.description, start=task.start, total=0
                                    ),
                                ),
                            ),
                        )
                        thread.start()
                        threads.append(thread)
                    for thread in threads:
                        thread.join()

            print()
            autorun()
        else:
            rich_print(
                "Autorun nebyl spuštěn kvůli nepodařené/nekompletní inicializaci",
                color="yellow",
            )

    if "exit" not in args.commands and (not args.no_import or args.auto_run):
        print()
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_aware = (
            datetime.now()
            .astimezone()
            .replace(hour=0, minute=0, second=0, microsecond=0)
        )

        first = True
        for znamka in filter(
            lambda x: min(lasttime, today - timedelta(5)) < x.date1 and x.grade != "?",
            api.looting.get(bakalariapi.Grade),
        ):
            if first:
                first = False
                print("Poslední známky:")
            note = znamka.note1.strip() or znamka.note2.strip()
            rich_print(
                f"Z předmětu [magenta]{znamka.subject}[/magenta] známka [bright_green]{znamka.grade}[/bright_green] ze dne {znamka.date1.strftime('%d. %m. %Y')}"
                + ("" if note == "" else f" - {note}")
            )

        first = True
        for komens in filter(
            lambda x: x.grade == "?", api.looting.get(bakalariapi.Grade)
        ):
            if first:
                first = False
                print("Nadcházející klasifikace:")
            rich_print(
                f"Z předmětu [magenta]{komens.subject}[/magenta] na {komens.date1.strftime('%d. %m. %Y')}"
            )

        first = True
        for schuzka in filter(
            lambda x: today_aware < x.start_time
            and x.start_time < today_aware + timedelta(2),
            api.looting.get(bakalariapi.Meeting),
        ):
            if first:
                first = False
                print("Dnešní a zítřejší schůzky:")
            rich_print(
                f"{schuzka.start_time.strftime('%H:%M %d. %m. %Y')} - {'[bright_black]Neznámý[/bright_black]' if schuzka.owner is None else f'[magenta]{schuzka.owner.name}[/magenta]'} \"{schuzka.name.strip()}\""
            )

        first = True
        for ukol in filter(lambda x: not x.done, api.looting.get(bakalariapi.Homework)):
            if first:
                first = False
                print("Úkoly:")
            ukol._sort_by_date
            rich_print(
                f"Z předmětu [magenta]{ukol.subject}[/magenta] na {ukol.submission_date.strftime('%d. %m.')} - {ukol.content}"
            )

        first = True
        for znamka in filter(
            lambda x: (x.need_confirm and not x.confirmed)
            or min(lasttime, today - timedelta(5)) < x.time,
            api.looting.get(bakalariapi.Komens),
        ):
            if first:
                first = False
                print("Komens zprávy:")
            rich_print(
                f"Komens zpráva od [magenta]{znamka.sender}[/magenta] z {znamka.time.strftime('%H:%M %d. %m. %Y')}"
                + (
                    " [yellow](nepotvrzená)[/yellow]"
                    if (znamka.need_confirm and not znamka.confirmed)
                    else ""
                )
            )

        with get_io_file(TIME_FILE, True) as f:
            f.write(datetime.now().isoformat())

    if len(args.commands) != 0:
        if successful_init:
            print("Vykonávám zadané příkazy...")
            for command in args.commands:
                print(command)
                shell_instance.proc_string(command)
        else:
            rich_print(
                "Zadané příkazy nebyly spuštěny kvůli nepodařené/nekompletní inicializaci",
                color="yellow",
            )

    try:
        shell_instance.start_loop()
    except (shell.DummyShellError, KeyboardInterrupt):
        Command_Konec(False)


def prepare_shell():
    global shell_instance
    predefined_commands = [x for x in shell.ShellPredefinedCommands]
    predefined_commands.remove(shell.ShellPredefinedCommands.EXIT)
    _globals = globals()
    _globals["p"] = rich_print
    _globals["i"] = rich.inspect
    shell_instance = shell.Shell(
        # prompt="[bright_green]BakalariAPI Shell[/bright_green][yellow]>[/yellow]",
        prompt="BakalariAPI Shell>",
        allow_python_exec=True,
        python_exec_prefix=" ",
        python_exec_globals=_globals,
        python_exec_locals=locals(),
        predefined_commands=predefined_commands,
        command_exception_traceback=True,
        command_exception_traceback_locals=True,
        command_exception_reraise=False,
        raise_on_ctrlc=True,
        end_on_ctrlc=True,
        dummy_shell="exit" in args.commands,
    )
    parser_fresh = shell.ShellArgumentParser(add_help=False)
    parser_fresh.add_argument(
        "-f",
        "--fresh",
        help="Pokud je tato flaga přítomna, vynutí se získání dat ze serveru",
        default=False,
        action="store_true",
        dest="force_fresh",
    )

    parser = shell.ShellArgumentParser(parents=[parser_fresh])
    parser.add_argument(
        "limit",
        type=int,
        nargs="?",
        default=None,
        help="Limituje počet zpráv, které se načtou a tím i zrychlí proces",
    )
    shell_instance.add_command(
        shell.Command(
            "komens",
            Command_Komens,
            short_help="Zobrazí komens zprávy",
            argparser=parser,
            spread_arguments=True,
            aliases=["zpravy"],
        )
    )
    shell_instance.add_command(
        shell.Command(
            "znamky",
            Command_Znamky,
            short_help="Zobrazí známky",
            argparser=shell.ShellArgumentParser(parents=[parser_fresh]),
        )
    )
    shell_instance.add_command(
        shell.Command(
            "schuzky",
            Command_Schuzky,
            short_help="Zobrazí (nadcházející) schůzky",
            argparser=shell.ShellArgumentParser(parents=[parser_fresh]),
        )
    )
    shell_instance.add_command(
        shell.Command(
            "studenti",
            Command_Studenti,
            short_help="Zobrazí studenty",
            argparser=shell.ShellArgumentParser(parents=[parser_fresh]),
        )
    )
    parser = shell.ShellArgumentParser()
    parser.add_argument("ID", help="ID testu, který se má spustit")
    shell_instance.add_command(
        shell.Command(
            "test",
            RunTest,
            argparser=parser,
            short_help="Spustí daný test",
            spread_arguments=True,
        )
    )
    parser = shell.ShellArgumentParser(parents=[parser_fresh])
    parser.add_argument(
        "-s",
        "--slow",
        help="Pokud je tato flaga přítomna, úkoly budou získány v 'pomalém módu'",
        action="store_false",
        dest="fast",
        default=True,
    )
    shell_instance.add_command(
        shell.Command(
            "ukoly",
            Command_Ukoly,
            argparser=parser,
            short_help="Zobrazí úkoly",
            spread_arguments=True,
        )
    )
    shell_instance.add_command(
        shell.Command(
            "server",
            ServerInfo,
            short_help="Zobrazí informace o serveru",
        )
    )
    parser = shell.ShellArgumentParser()
    parser.add_argument(
        "-f",
        "--force",
        help="Pokud je tato flaga přítomna, neprovede se odlášení sessionů a aplikace se tedy rychleji ukončí",
        action="store_false",
        default=True,
        dest="nice",
    )
    shell_instance.add_command(
        shell.Command(
            "exit",
            Command_Konec,
            argparser=parser,
            short_help="Ukončí shell",
            spread_arguments=True,
        )
    )
    parser = shell.ShellArgumentParser()
    parser.add_argument(
        "file_name",
        nargs="?",
        help="ID/jméno exportu",
        default="main",
        metavar="ID",
    )
    shell_instance.add_command(
        shell.Command(
            "export",
            Command_Export,
            argparser=parser,
            short_help="Exportuje data z daného souboru",
            spread_arguments=True,
        )
    )
    parser = shell.ShellArgumentParser()
    parser.add_argument(
        "file_name",
        nargs="?",
        help="ID/jméno importu",
        default="main",
        metavar="ID",
    )
    shell_instance.add_command(
        shell.Command(
            "import",
            Command_Import,
            argparser=parser,
            short_help="Importuje data z daného souboru",
            spread_arguments=True,
        )
    )
    shell_instance.add_command(
        shell.Command("init", Init, short_help="Provede (opětovnou) inicializaci")
    )

    parser = shell.ShellArgumentParser()
    subparsers = parser.add_subparsers(
        required=True,
        metavar="příkaz",
        dest="cmd",
        parser_class=shell.ShellArgumentParser,
    )
    subparsers.add_parser(
        "show",
        help="Zobrazí uloženou konfiguraci",
    )
    subparsers.add_parser(
        "save",
        help="Uloží současnou konfiguraci",
    )
    subparsers.add_parser(
        "remove",
        help="Odstraní uloženou konfiguraci",
    )
    subparsers.add_parser(
        "check",
        help="Zobrazí údaje o uložené konfiguraci",
    )
    subparsers.add_parser(
        "open",
        help="Otevře konfigurační složku",
    )
    shell_instance.add_command(
        shell.Command(
            "config",
            Command_Config,
            argparser=parser,
            short_help="Příkaz na práci s uloženou konfigurací",
            spread_arguments=False,
        )
    )


if __name__ == "__main__":
    main()
