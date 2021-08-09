from __future__ import annotations

import argparse
import asyncio
import getpass
import io
import json
import logging
import logging.config
import os
import sys
import threading
import time
import traceback
import warnings
import webbrowser
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Callable, cast, Any

import appdirs
import bakalariapi
from bs4 import BeautifulSoup
from prompt_toolkit.input import create_input
from prompt_toolkit.key_binding import KeyPress
from prompt_toolkit.keys import Keys
from prompt_toolkit.shortcuts.progress_bar import ProgressBar, ProgressBarCounter

# Import kvůli tomu, aby jsme mohli volat rovnou 'inspect()' v python execu ze shellu
from rich import inspect
from rich import print as rich_print
from rich.console import Console
from rich.logging import RichHandler
from rich.syntax import Syntax

# Takový hack na to, aby `bakalarishell` šel spustit také přímo ze zdrojové složky
# Pokud se `bakalarishell` spustí jako modul (= přes `import`), tak vše proběhne v pořádku
# Pokud se ale spustí přes "python main.py" nebo "python bakalarishell", tak relativní
# `import` selže ("ImportError: attempted relative import with no known parent package")
# a `shell` se naimportuje "přímo" (resp. ne relativně), což už je v pořádku.
# Pozn.: Pokud někdo dumá nad tím, proč zde tedy není jen druhá možnost, tak to je
# kvůli tomu, že ta zase pro změnu nefugnuje při importu jako modul, jelikož v tom případě
# hledá modul `shell` jako "globální" modul (ne jako "lokální" ve složce), tudíž selže.
try:
    from . import shell
except ImportError:
    import shell

cls = shell.cls

api: bakalariapi.BakalariAPI
shell_instance: shell.Shell
dirs = appdirs.AppDirs(appauthor="BakalariAPI", appname="bakalarishell", roaming=True)
CONFIG_FILE_PATH = os.path.join(dirs.user_config_dir, "config.json")


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
    disable_config: bool = False

    commands: list[str] = field(default_factory=list)


args: Args

##################################################
#####                 FUNKCE                 #####
##################################################


def partial_init_notice():
    rich_print(
        '[yellow]Tuto akci nelze vykonat, jelikož shell se nachází v omezeném módu. Pro přepnutí do online módu můžete zkusit příkaz "init".[/yellow]'
    )


def dialog_ano_ne(
    text: str = "", default: bool | None = None, color: str | None = None
) -> bool:
    message = f"{text} Ano/Ne{'' if default is None else (' (Ano)' if default else ' (Ne)')}: "
    while True:
        # ano/true/yes/1 / ne/false/no/0
        if color is not None:
            rich_print(f"[{color}]{message}[/{color}]", end="")
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
    while True:
        inpt = input(text + ("" if default is None else f" ({default})"))
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
            # Pyright nebere v potaz IF z outer scopu (https://github.com/microsoft/pyright/issues/1731)
            o = cast(bakalariapi.Komens, obj)
            if key_press.key == "p":
                print("Potvrzuji zprávu...")
                o.confirm(api)
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
            o = cast(
                bakalariapi.Meeting, obj
            )  # Pyright nebere v potaz IF z outer scopu
            key = key_press.key.lower()
            if key == "o":
                webbrowser.open(o.join_url)
            elif key == "z":
                c = Console()
                c.print(
                    Syntax(
                        str(BeautifulSoup(o.content, "html.parser").prettify()), "html"
                    )
                )

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
            o = cast(bakalariapi.Homework, obj)
            key = key_press.key.lower()
            if key == "h":
                o.mark_as_done(api, True)
                print("Úkol označen jako hotový")
            elif key == "n":
                o.mark_as_done(api, False)
                print("Úkol označen jako nehotový")
            elif key == "z":
                c = Console()
                c.print(
                    Syntax(
                        str(BeautifulSoup(o.content, "html.parser").prettify()), "html"
                    )
                )

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
            elif not mask_keyboard_interrupt and key_press.key == Keys.ControlC:
                raise KeyboardInterrupt
            elif handler is not None:
                handler(key_press, done)

    with inpt.raw_mode():
        with inpt.attach(lambda: key_handler_proc(inpt.read_keys())):
            await evnt.wait()


def get_io_file(file: str, mode: str = "r+") -> io.IO:
    """Vytvoří a vrátí file handler na daný soubor `file` v uživatelské (data) složce."""
    path = os.path.join(dirs.user_data_dir, file)
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "x"):
            pass
    return open(path, mode)


def save_config():
    if not os.path.exists(CONFIG_FILE_PATH):
        os.makedirs(os.path.dirname(CONFIG_FILE_PATH), exist_ok=True)
        with open(CONFIG_FILE_PATH, "x"):
            pass
    with open(CONFIG_FILE_PATH, "w") as f:
        # Indent, protože chci, aby to šlo přehledně upravit i z editoru (i když k tomu nejspíše nikdy nedojde)
        # (a navíc alespoň nemusí řešit formátování při "config show")
        json.dump(args.__dict__, f, indent=4)


##################################################
#####             PŘÍKAZO-FUNKCE             #####
##################################################


def Init():
    def partial_init_mode():
        rich_print(
            "\n[yellow]Inicilizace neproběhla úspěšně a shell poběží v omezeném módu.[/yellow]"
        )

    if args.url is None:
        try:
            args.url = input("URL adresa serveru: ")
            api.server_info.url = args.url
        except KeyboardInterrupt:
            rich_print("[red]\nNebyla zadána adresa serveru![/red]")
            partial_init_mode()
            return
    if args.username is None:
        try:
            args.username = input("Přihlašovací jméno: ")
            api.username = args.username
        except KeyboardInterrupt:
            rich_print("[red]\nNebylo zadáno přihlašovací jméno![/red]")
            partial_init_mode()
            return
    if args.password is None:
        try:
            args.password = getpass.getpass("Heslo: ")
        except KeyboardInterrupt:
            rich_print(
                "[yellow]\nHeslo nebylo zadáno, předpokládá se prázdné heslo[/yellow]"
            )
            args.password = ""
        api.password = args.password

    print(f"Kontrola stavu serveru/webu... ({api.server_info.url})")
    if not api.is_server_running():
        try:
            if dialog_ano_ne(
                "Server/web (pravděpodobně) neběží; Chce se pokusit naimportovat data z předchozího souboru?",
                True,
                "yellow",
            ):
                Command_Import()
            else:
                partial_init_mode()
                return
        except KeyboardInterrupt:
            partial_init_mode()
            return
    print("Sever/web běží")
    print(f"Kontrola přihlašovacích údajů pro uživatele '{api.username}'")
    if not api.is_login_valid():
        rich_print("[red]Přihlašovací údaje jsou neplatné![/red]")
        partial_init_mode()
        return
    print("Přihlašovací údaje ověřeny a jsou správné")
    print("Nastavuji...")
    with warnings.catch_warnings():
        # Nechceme dostat `VersionMismatchWarning`, protože v `SeverInfo()` kontrolujeme verzi manuálně
        warnings.simplefilter("ignore")
        api.init()
    print("Nastaveno:")
    ServerInfo()


def ServerInfo():
    print(
        f"Typ uživatele: {'Není k dispozici' if api.user_info.type == '' else api.user_info.type}\n"
        f"Uživatelký hash: {'Není k dispozici' if api.user_info.hash == '' else api.user_info.hash}\n"
        f"Verze Bakalářů: {'Není k dispozici' if api.server_info.version == '' else api.server_info.version}\n"
        f"Datum verze Bakalářů: {'Není k dispozici' if api.server_info.version_date is None else api.server_info.version_date.strftime('%d. %m. %Y')}\n"
        f"Evidenční číslo verze Bakalářů: {'Není k dispozici' if api.server_info.evid_number is None else api.server_info.evid_number}"
    )
    if not api.is_version_supported():
        print("*** Jiná verze Bakalářů! Všechny funkce nemusejí fungovat správně! ***")


def Command_Komens(limit: int | None = None, force_fresh: bool = False):
    def fresh() -> list[bakalariapi.Komens]:
        if api.is_partial_init:
            partial_init_notice()
            return []
        output: list[bakalariapi.Komens] = []
        with ProgressBar("Získávám zprávy...") as progress_bar:
            counter = progress_bar(remove_when_done=True)
            unresolved = api._parse(
                bakalariapi.modules.komens.getter_komens_ids(api)
            ).get(bakalariapi.UnresolvedID)[:limit]
            counter.total = len(unresolved)
            progress_bar.invalidate()
            for unresolved_id in unresolved:
                output.append(api._resolve(unresolved_id).get(bakalariapi.Komens)[0])
                counter.item_completed()
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
        print("Nebyli nalezeny žádné aktualní schůzky")
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
        with ProgressBar("Získávám schůzky...") as progress_bar:
            counter = progress_bar(remove_when_done=True)
            unresolved = api._parse(
                bakalariapi.modules.meetings.getter_future_meetings_ids(api)
            ).get(bakalariapi.UnresolvedID)
            counter.total = len(unresolved)
            progress_bar.invalidate()
            for unresolved_id in unresolved:
                output.append(api._resolve(unresolved_id).get(bakalariapi.Meeting)[0])
                counter.item_completed()
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
        print("Nebyli nalezeny žádné aktualní schůzky")
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
    count = dialog_cislo("Kolik zobrazit výsledků najednou? (Výchozí 25) ", 25)
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
        print("Nebyli nalezeny žádné aktualní úkoly")
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
    with get_io_file(file_name) as f:
        f.write(api.looting.export_json())
        # Odstraníme data, která jsou případně po JSONu, co jsme teď napsali (třeba pozůstatek po předchozím JSONu, pokud byl delší, jak náš současný)
        f.truncate()
    print(f"JSON data vygenerována a zapsána do souboru '{file_name}'")


def Command_Import(file_name: str = "main"):
    with get_io_file(file_name) as f:
        api.looting.import_json(f.read())
    print(f"Data ze souboru '{file_name}' byla načtena")


def Command_Config(namespace: dict[str, Any]):
    cmd = namespace["cmd"]
    if cmd == "show":
        if not os.path.exists(CONFIG_FILE_PATH):
            print("Žádná konfigurace není uložená")
        else:
            with open(CONFIG_FILE_PATH, "r") as f:
                c = Console()
                c.print(Syntax(f.read(), "json"))
    elif cmd == "save":
        save_config()
        print("Konfigurace uložena")
    elif cmd == "remove":
        if os.path.exists(CONFIG_FILE_PATH):
            os.remove(CONFIG_FILE_PATH)
            print("Konfigurace byla vymazána")
        else:
            print("Nic se nevykonalo, jelikož konfigurace není uložená")
    elif cmd == "check":
        if os.path.exists(CONFIG_FILE_PATH):
            s = os.stat(CONFIG_FILE_PATH)

            s.st_mtime
            rich_print(
                f"Konfigurace je uložená z data {datetime.fromtimestamp(s.st_mtime).strftime('%d. %m. %Y, %H:%M:%S')}, velikost konfigurace je {s.st_size}B"
            )
        else:
            print("Žádná konfigurace není uložená")


##################################################
#####                TESTY                   #####
##################################################


def RunTest(ID: int):
    m = __import__(__name__)
    t = f"Test{ID}"
    if hasattr(m, t):
        print(f"Zahajuji test {ID}")
        try:
            o = getattr(m, t)()
            print(
                f"Test {ID} skončil" + ("" if o is None else f"; Výsledek testu je {o}")
            )
        except:
            print("Test skončil neúspěchem:")
            traceback.print_exc()
    else:
        print(f"Test {ID} nenalezen")


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
    print("Vytváření kopie skrz JSON export/import...")
    new = bakalariapi.looting.Looting()
    json = api.looting.export_json()
    print(json)
    new.import_json(json)
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
    print("IDčka online schůzek získany")
    print()
    error: list[bakalariapi.UnresolvedID[bakalariapi.Meeting]] = []
    try:
        with ProgressBar() as pb:
            counter = pb(IDs)
            for ID in counter:  # type: ignore
                counter.label = f"Schůzka {ID.ID}"
                try:
                    api._resolve(ID)
                except bakalariapi.exceptions.BakalariQuerrySuccessError as e:
                    print(f"Online schůzku {ID.ID} se nepodařilo načíst ({e})")
                    error.append(ID)
    except KeyboardInterrupt:
        pass
    finally:
        la = len(IDs)
        le = len(error)
        print(f"Úspěšné pokusy: {la - le}; Neúspěšné pokusy: {le}")


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
        if not os.path.exists(CONFIG_FILE_PATH):
            return None
        with open(CONFIG_FILE_PATH, "r") as f:
            parsed = json.load(f)
        return parsed

    parser = argparse.ArgumentParser(
        description="Shell integrující funkcionalitu BakalářiAPI",
        epilog="Ano, ano, ano... Actually je to web scraper, ale API zní líp :)",
    )
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
        "-v",
        "--verbose",
        help="Zapne shell v 'ukecaném módu'; Lze opakovat vícekrát pro větší 'ukecanost' (max 5).",
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

    if not args.no_init:
        Init()

    if args.test is not None:
        RunTest(args.test)

    prepare_shell()
    # Chceme `main()` locals, ne `prepare_shell()` locals
    shell_instance.PYTHON_EXEC_LOCALS = locals()

    if args.auto_run:
        # Takže... Tohle bude, je a už i byl pain - strávil jsem na tomto X dnů a pořád jsem to
        # nezprovoznil. V tuhle chvíli prohlašuji, že to nejde. Dle mého jsem zkusil vše - různě umístěný
        # patch_stdout, různě umístěný ProgressBar(), rozdílé místa, odkud se volají různé thready. Jsou
        # tu i další věci, co chci dělat tudíž tohle odkládám na někdy jindy.
        # Problém je ten, že ProgressBar si nerozumí s prompt (obv, protože kdyby si rozumněli, tak není
        # co řešit). Jde hlavně o 2 věci: 1. Když máme prompt aktivní, tak nelze psát do terminálu,
        # 2. ProgressBar potřebuje přepisovat to co napsal (tzn. \r (i guess)). První problém má jasné
        # řešení - patch_stdout. Jenže zde se stává z druhého bodu problém (který dosud nebyl, protože
        # ProgressBar mohl v pohodě přepisovat to co napsal) - patch_stdout očividně "nepodporuje"
        # přepisování (tzn. \r (opět jen můj tip)), pokud je zde aktivní prompt (když se nad tím zamyslíte,
        # tak ono udělat takovou věc (tím myslím podporovat přepisování) je docela insane, když potřebujete
        # NEpřepsat tu jednu řádku, která je od promptu - tím se nesnažím říct, že je to tak správně, jen
        # říkám, že to až tak EZ není).
        # Testy, které jsem zkoušel dopadli od katastrofických výsledků k ještě horším výsledkům. Zkoušel
        # jsem jen s jednou instancí ProgressBarCounter (tzn. jen jedna řádka, která se potřebuje přepsat),
        # ale stejně to dopadlo tak jak to dopadlo. V "lepších" případech se "jen" promíchal prompt
        # s ProgressBarem. V horších případech nastali exceptiony v asyncio a promt_toolkit modulech.
        # V nejhorším případě jsem nějak způsobil exceptiony v stdlib modulech, které se navíc lišily
        # v jednotivých pokusech (bez změny v kódu)! Ano, přeci jen je to i theading, takže se chování
        # programu může *teoreticky* lišit v jednotivých pokusech, ale twl - je to stdlib! To má být
        # spolehlivý a ten, kdo to použije by neměl řešit nějaký takovýhle chyby. (Pozn.: Tyhle exceptiony
        # byly "interní" - Tím myslím, že se stali hoooodně hluboko v knihovně a nikde k něčemu takovému není
        # dokumentace (ani StackOverflow nepomohl)).
        # Závěr? Nejde to. Well jde, pokud hodlám přepsat prompt_toolkit nebo si napsat vlastní prompt_toolkit.
        # Reálně ono by asi stačilo upravit patch_stdout (interně v prompt_toolkit je to tuším StdoutProxy),
        # jelikož ono to "drží" prompt pořád dole, takže by někde stačilo "jen" říct že "progress bar taky
        # nech dole", ale to vážně dělat nechci. Je dost možný, že se na to vykašlu a otevřu prostě GitHub
        # issue, ať to za mě implementuje někdo jiný eShrug.
        # BTW asi by to šlo vyřešit i tak, že si prostě udlěmám prompt_tookit aplikaci (tzn. že promt_toolkitu
        # nechám celý terminál, ať si s ním dělá co chce), ale tzn. že shell pak vlastně potřebuje být taky
        # jako aplikace (chci nechat shell jako stand alone modul, ne jen něco, co mi dělá funkcionalitu pro
        # BakalářiAPI) a IDK jestli pak nenastane stejný problém.

        def task_ukoly(api: bakalariapi.BakalariAPI, progress_bar: ProgressBarCounter):
            length = len(api.get_homeworks(bakalariapi.GetMode.FRESH, fast_mode=True))
            progress_bar.total = length
            # 'item_completed()' dělá to, že zvýší 'items_completed' o 1 a zároveň volá 'invalidate()' na 'progress_bar' instanci, takže uděláme +/- to samé
            # (pozn. zde máme 'progress_bar' jako ProgressBarCounter, ale ProgressBarCounter má vlastní 'progress_bar')
            progress_bar.items_completed = length
            progress_bar.progress_bar.invalidate()

        def task_komens(api: bakalariapi.BakalariAPI, progress_bar: ProgressBarCounter):
            unresolved = api._parse(
                bakalariapi.modules.komens.getter_komens_ids(api)
            ).get(bakalariapi.UnresolvedID)
            progress_bar.total = len(unresolved)
            for unresolved_id in unresolved:
                api._resolve(unresolved_id)
                progress_bar.item_completed()

        def task_znamky(api: bakalariapi.BakalariAPI, progress_bar: ProgressBarCounter):
            length = len(api.get_all_grades())
            progress_bar.total = length
            progress_bar.items_completed = length
            progress_bar.progress_bar.invalidate()  # viz task_ukoly

        def task_schuzky(
            api: bakalariapi.BakalariAPI, progress_bar: ProgressBarCounter
        ):
            # unresolved = api._parse(bakalariapi.modules.meetings.getter_meetings_ids(api, datetime(1, 1, 1), datetime(9999, 12, 31, 23, 59, 59))).retrieve_type(bakalariapi.UnresolvedID)
            unresolved = api._parse(
                bakalariapi.modules.meetings.getter_future_meetings_ids(api)
            ).get(bakalariapi.UnresolvedID)
            progress_bar.total = len(unresolved)
            for unresolved_id in unresolved:
                api._resolve(unresolved_id)
                progress_bar.item_completed()

        class Task:
            def __init__(
                self,
                name: str,
                func: Callable[[bakalariapi.BakalariAPI, ProgressBarCounter], None],
            ) -> None:
                self.name: str = name
                self.func: Callable[
                    [bakalariapi.BakalariAPI, ProgressBarCounter], None
                ] = func

            def run(self, progress_bar: ProgressBarCounter):
                self.func(api, progress_bar)

        tasks = [
            Task("Získání Komens zpráv", task_komens),
            Task("Získání schůzek", task_schuzky),
            Task("Získání úkolů", task_ukoly),
            Task("Získání známek", task_znamky),
        ]

        def autorun():
            # Absolutně nevím, k čemu jsem se dostal a abosultně nemám tušení, co teď dělám - Jakože vůbec.
            # Jen jsem se kouknul na nějakých 50 řádek asyncia (o kterým vím jen to, že to má být asynchroní)
            # a usoudil, že tohle je ASI fix na neexistující event loop ve threadu (kvůli progress baru, který
            # využívá funkci (z asyncia) 'get_event_loop()', která spoléhá na existující event loop (a pokud
            # ho nemá, tak hází RuntimeError exception)).
            # TL;DR: Pls někdo, kdo zná asyncio, to za mě opravte (někdo = nejspíše moje budoucí já, které se
            # bude muset asyncio naučit)
            # get_event_loop_policy().set_event_loop(get_event_loop_policy().new_event_loop())

            with ProgressBar("Úlohy po spuštění:") as progress_bar:

                def task_runner(task: Task):
                    task.run(progress_bar(label=task.name))

                threads = []
                for task in tasks:
                    thread = threading.Thread(target=task_runner, args=(task,))
                    threads.append(thread)
                    thread.start()
                for thread in threads:
                    thread.join()
                time.sleep(1)

        print()
        # threading.Thread(target=autorun).start()
        autorun()

    print()
    print("Shell aktivní")

    if len(args.commands) != 0:
        print("Vykonávám zadané příkazy...")
        for command in args.commands:
            print(command)
            shell_instance.proc_string(command)

    try:
        shell_instance.loop()
    except KeyboardInterrupt:
        Command_Konec(False)


def prepare_shell():
    global shell_instance
    predefined_commands = [x for x in shell.ShellPredefinedCommands]
    predefined_commands.remove(shell.ShellPredefinedCommands.EXIT)
    shell_instance = shell.Shell(
        prompt="BakalariAPI Shell>",
        allow_python_exec=True,
        python_exec_prefix=" ",
        python_exec_globals=globals(),
        python_exec_locals=locals(),
        predefined_commands=predefined_commands,
        command_exception_traceback=True,
        command_exception_traceback_locals=True,
        command_exception_reraise=False,
        raise_on_ctrlc=True,
        end_on_ctrlc=True,
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
