from __future__ import annotations

import argparse
import asyncio
import io

# from asyncio import get_event_loop_policy # Ok, teď absolutně nemám tušení co dělám (jakože vůbec), ale doufám, že to takhle zprovozním
import logging
import logging.config
import sys
import threading
import time
import traceback
import webbrowser

from datetime import (
    datetime,
    timedelta,
    timezone,
)

from typing import Callable

from bs4 import BeautifulSoup

from prompt_toolkit.key_binding import KeyPress
from prompt_toolkit.shortcuts.progress_bar import ProgressBar, ProgressBarCounter
from prompt_toolkit.input import create_input
from prompt_toolkit.keys import Keys

from rich import (
    inspect,
)  # Import kvůli tomu, aby jsme mohli volat rovnou 'inspect()' v python execu ze shellu
from rich.console import Console
from rich.logging import RichHandler
from rich.syntax import Syntax

import bakalariapi
from . import shell
from .shell import cls

api: bakalariapi.BakalariAPI
shell_instance: shell.Shell

##################################################
#####                 FUNKCE                 #####
##################################################


def dialog_ano_ne(text: str = "", default: bool | None = None) -> bool:
    while True:
        inpt = input(
            f"{text} Ano/Ne{'' if default is None else (' (Ano)' if default else ' (Ne)')}: "
        )  # ano/true/yes/1 / ne/false/no/0
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


def show(obj: bakalariapi.objects.BakalariObject, title: str | None = None):
    if title is not None:
        print(title)

    if isinstance(obj, bakalariapi.Komens):
        print(obj.format())
        print("\n\n\n")
        if (
            obj.need_confirm
            and not obj.confirmed
            and dialog_ano_ne("Zpráva vyžaduje potvrzení. Chcete potvrdit přečtení?")
        ):
            print("Potvrzuji zprávu...")
            obj.confirm(api)
            print("Zpráva potvrzena")

        print(
            "Enter - Pokračování, P - Potrvrdí přečtení zprávy"
        )  # TODO: Barvičky kláves
        print()

        def komens_key_handler(key_press, done):
            if key_press.key == "p":
                print("Potvrzuji zprávu...")
                obj.confirm(api)  # type: ignore # Protože pyright nebere v nested funkci v potaz IFy (takže obj je pořád *jen* BakalariObject)
                print("Zpráva potvrzena")

        asyncio.run(keyhandler(komens_key_handler))

    elif isinstance(obj, bakalariapi.Grade):
        print(obj.format())
        print("\n")
        print("Enter - Pokračování, Z - Zobrazí JSON data")

        def grade_key_handler(key_press: KeyPress, done: Callable):
            return
            key = key_press.key.lower()
            if key == "z":
                c = Console()
                c.print(Syntax(str(BeautifulSoup(obj.content, "html.parser").prettify()), "html"))  # type: ignore # viz výš

        asyncio.run(keyhandler(grade_key_handler))

    elif isinstance(obj, bakalariapi.Meeting):
        print(obj.format())
        print("\n\n")

        print(
            "Enter - Pokračování, O - Otevře schůzku v prohlížeči, Z - Zobrazí HTML pozvánky"
        )  # TODO: Barvičky kláves

        def meeting_key_handler(key_press: KeyPress, done: Callable):
            key = key_press.key.lower()
            if key == "o":
                webbrowser.open(obj.joinURL)  # type: ignore # viz výš
            elif key == "z":
                c = Console()
                c.print(Syntax(str(BeautifulSoup(obj.content, "html.parser").prettify()), "html"))  # type: ignore # viz výš

        asyncio.run(keyhandler(meeting_key_handler))
    elif isinstance(obj, bakalariapi.Student):
        pass

    elif isinstance(obj, bakalariapi.Homework):
        print(obj.format())
        print("\n\n")

        print(
            "Enter - Pokračování, H - Označí úkol jako hotový, N - Označí úkol jako nehotový, Z - Zobrazí HTML úkolu"
        )  # TODO: Barvičky kláves
        print()

        def homework_key_handler(key_press: KeyPress, done: Callable):
            key = key_press.key.lower()
            if key == "h":
                obj.mark_as_done(api, True)  # type: ignore # viz výš
                print("Úkol označen jako hotový")
            elif key == "n":
                obj.mark_as_done(api, False)  # type: ignore # viz výš
                print("Úkol označen jako nehotový")
            elif key == "z":
                c = Console()
                c.print(Syntax(str(BeautifulSoup(obj.content, "html.parser").prettify()), "html"))  # type: ignore # viz výš

        asyncio.run(keyhandler(homework_key_handler))

    else:
        raise Exception(f"Undefined type '{type(obj)}' to show")


async def keyhandler(
    handler: Callable[[KeyPress, Callable[[], None]], None],
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
        done_on_enter:
            Pokud True, tak se při klávese Enter ukončí záznam kláves.
            Pozn.: Pokud True, tak se funkce v parametru handler nevolá.

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
            else:
                handler(key_press, done)

    with inpt.raw_mode():
        with inpt.attach(lambda: key_handler_proc(inpt.read_keys())):
            await evnt.wait()


def check_io_file() -> bool:
    """Zkontroluje, jestli je specifikován I/O soubor, případně vyzve uživatele o vytvoření.

    Returns:
        Pokud soubor již existoval či uživatel vytvořil nový, vratí `True`, jinak `False`.
    """
    if parsed_args.file is None:
        try:
            if dialog_ano_ne(
                "Nebyl nalezen vstupní/výstupní soubor. Chcete určit soubor?"
            ):
                name = input("Název souboru: ")
                try:
                    parsed_args.file = open(name, "x")
                except FileExistsError:
                    if dialog_ano_ne(
                        f"Soubor s jménem '{name}' již existuje. Pokud bude tento soubor použit, jeho obsah může být smazán. Chcete ho přesto použít?"
                    ):
                        parsed_args.file = open(name, "r+")
                    else:
                        return False
                return True
            else:
                return False
        except KeyboardInterrupt:
            return False
    return True


##################################################
#####             PŘÍKAZO-FUNKCE             #####
##################################################


def Init():
    print(f"Kontrola stavu serveru/webu... ({api.server_info.url})")
    if not api.is_server_running():
        if dialog_ano_ne(
            "Server/web (pravděpodobně) neběží; Chce se pokusit naimportovat data z předchozího souboru?",
            True,
        ):
            Command_Import()
        elif dialog_ano_ne("Chce tedy ukončit aplikaci?", True):
            sys.exit(1)
        else:
            print(
                "Nechávám aplikaci běžet, avšak většina věcí pravděpodobně fungovat nebude"
            )
            return
    print("Sever/web běží")
    print(f"Kontrola přihlašovacích údajů pro uživatele '{api.username}'")
    if not api.is_login_valid():
        print("Přihlašovací údaje jsou neplatné!")
        if dialog_ano_ne("Chce tedy ukončit aplikaci?", True):
            sys.exit(1)
        else:
            print(
                "Nechávám aplikaci běžet, avšak většina věcí pravděpodobně fungovat nebude"
            )
            return
    print("Přihlašovací údaje ověřeny a jsou správné")
    print("Nastavuji...")
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
    if (
        api.server_info.version is not None
        and api.server_info.version != bakalariapi.LAST_SUPPORTED_VERSION
    ):
        print("*** Jiná verze Bakalářů! Všechny funkce nemusejí fungovat správně! ***")


def Command_Komens(limit: int | None = None, force_fresh: bool = False):
    def fresh() -> list[bakalariapi.Komens]:
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

    znamky = api.get_grades(
        bakalariapi.GetMode.FRESH
        if force_fresh
        else bakalariapi.GetMode.CACHED_OR_FRESH
    )

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

    studenti = api.get_students(
        bakalariapi.GetMode.FRESH
        if force_fresh
        else bakalariapi.GetMode.CACHED_OR_FRESH
    )

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
    if not parsed_args.file is None:
        parsed_args.file.close()


def Command_Export():
    if not check_io_file():
        print("Nelze exportovat data, jelikož není specifikován soubor")
        return
    print("Generace JSON dat...")
    f: io.TextIOWrapper = parsed_args.file
    f.write(api.looting.export_json())
    f.truncate()  # Odstraníme data, která jsou případně po JSONu, co jsme teď napsali (třeba pozůstatek po předchozím JSONu, pokud byl delší, jak náš současný)
    f.seek(0, 0)

    print(f"JSON data vygenerována a zapsána do souboru '{f.name}'")


def Command_Import():
    if not check_io_file():
        print("Nelze importovat data, jelikož není specifikován soubor")
        return
    f: io.TextIOWrapper = parsed_args.file
    api.looting.import_json(f.read())
    f.seek(0, 0)
    print(f"Data ze souboru {f.name} byla načtena")


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
    session = api.session_manager.get_session_or_create(
        bakalariapi.sessions.RequestsSession
    )
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
    finally:
        session.busy = False


def Test1():
    # Získáme si nějká data...
    # print("Získáváme data (schůzky + studenti)...")
    # API.get_fresh_meetings_future()
    # print("Data získána")

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
    global parsed_args
    parser = argparse.ArgumentParser(
        description="Rádoby 'API' pro Bakaláře",
        epilog="Ano, ano, ano... Actually je to web scraper, ale API zní líp :)",
    )
    parser.add_argument("url", help="URL na bakaláře (př. https://bakalari.skola.cz)")
    parser.add_argument(metavar="jmeno", help="Přihlašovací jméno", dest="user")
    parser.add_argument(metavar="heslo", help="Přihlašovací heslo", dest="password")
    parser.add_argument(
        "-b",
        "--browser",
        default="",
        choices=[x.name.lower() for x in bakalariapi.Browser],
        type=str.lower,  # => case-insensitive
        help="Specifikuje WebDriver prohlížeče, který použít",
    )
    parser.add_argument(
        "-e",
        "--executablePath",
        default=None,
        help="Cesta ke spustitelnému webdriveru pro prohlížeč, který je specifikovaný pomocí '-b'",
    )
    parser.add_argument(
        "-t",
        "--test",
        type=int,
        default=-1,
        help="Test, který se má spustit",
        dest="test2run",
        metavar="ID",
    )
    parser.add_argument(
        "-a",
        "--auto-run",
        help="Pokud je tato flaga přítomna, spustí se automatické úlohy",
        action="store_true",
        dest="auto_run",
        default=False,
    )
    parser.add_argument(
        "-n",
        "--no-init",
        help="Pokud je tato flaga přítomna, nebude BakalariAPI instance automaticky inicializována",
        action="store_true",
        dest="no_init",
        default=False,
    )
    parser.add_argument(
        "-v",
        "--verbose",
        help="Zapne shell v 'ukecaném módu'. Lze opakovat pro větší 'ukecanost' (max 5).",
        action="count",
        default=0,
    )
    parser.add_argument(
        "-f",
        "--file",
        type=argparse.FileType("r+", encoding="UTF-8"),
        help="Soubor na čtení a zápis výsledků",
    )
    parsed_args = parser.parse_args()

    # Verbose:
    #   0 - Nic
    #   1 - Warning; Pouze BakalářiAPI
    #   2 - Info; Pouze BakalářiAPI
    #   3 - Debug; Pouze BakalářiAPI
    #   4 - Info
    #   5 - NOSET
    if parsed_args.verbose != 0:
        logging.basicConfig(
            level=[
                None,
                "WARNING",
                "INFO",
                "DEBUG",
                "INFO",
                "NOTSET",
            ][parsed_args.verbose],
            datefmt="[%X]",
            handlers=[RichHandler()],
        )
        logging.info(
            "Logging zapnut na levelu %s (%s)",
            parsed_args.verbose,
            logging.getLevelName(logging.root.level),
        )
        if parsed_args.verbose < 4:
            for logger in [
                logging.getLogger(name) for name in logging.root.manager.loggerDict
            ]:
                if logger.name.startswith("bakalariapi"):
                    continue
                logger.propagate = False
            # logging.getLogger("bakalariapi").propagate = True

    seleniumSettings: bakalariapi.SeleniumHandler | None = None
    if parsed_args.browser != "":
        seleniumSettings = bakalariapi.SeleniumHandler(
            bakalariapi.Browser[parsed_args.browser.upper()],
            parsed_args.executablePath,
        )

    api = bakalariapi.BakalariAPI(
        parsed_args.url, parsed_args.user, parsed_args.password, seleniumSettings
    )

    if not parsed_args.no_init:
        Init()

    if parsed_args.test2run != -1:
        RunTest(parsed_args.test2run)

    prepare_shell()
    shell_instance.PYTHON_EXEC_LOCALS = (
        locals()
    )  # Chceme *main* locals, ne *prepare_shell* locals

    if parsed_args.auto_run:
        # Takže... Tohle bude, je a už i byl pain - dnes jsem na tom strávil celý den a pořád jsem to
        # nezprovoznil. V tuhle chvíli prohlašuji, že to nejde. Dle mého jsem zkusil vše - různě umístěný
        # patch_stdout, různě umístěný ProgressBar(), rozdílé místa, odkud se volají různé thready. Strávil
        # jsem u toho poměrně dost dlouhou dobu a jsou tu i další věci, co chci, aby ve verzi 2.0 byly,
        # tudíž tohle odkládám na potom.
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
    parser.add_argument("id", help="ID testu, který se má spustit")
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
    shell_instance.add_command(
        shell.Command(
            "export", Command_Export, short_help="Exportuje data z daného souboru"
        )
    )
    shell_instance.add_command(
        shell.Command(
            "import", Command_Import, short_help="Import data z daného souboru"
        )
    )
    shell_instance.add_command(
        shell.Command("init", Init, short_help="Provede (znovu) inicializaci")
    )


if __name__ == "__main__":
    main()
