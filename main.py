from __future__ import annotations

import argparse
import multiprocessing
import os
import time
import webbrowser
import traceback
from datetime import datetime, timedelta, timezone # Here it comes... Timezone hadndling first feel PepeLaugh
# Hej! Moje budoucí já... Já vím, že se sem jednou podíváš... Takže až ta chvíle nastane, tak si vzpomeň, že za 100 let budou tenhle samej problém
# s časovými pásmy řešit furt :) Takže nevadí, že si to pořád ještě po 10h debugu nespravil...
# HA! Dělám si srandu. Padej to opravit! S láskou - Tvoje minulé já :)

import bakalariapi
from bakalariapi import Endpoint
import shell

parser = argparse.ArgumentParser(
    description="Rádoby 'API' pro Bakaláře",
    epilog="Ano, ano, ano... Actually je to web scraper, ale API zní líp :)"
)
parser.add_argument(
    "url",
    help="URL na bakaláře (př. https://bakalari.skola.cz)"
)
parser.add_argument(
    "jmeno",
    help="Přihlašovací jméno"
)
parser.add_argument(
    "heslo",
    help="Přihlašovací jméno"
)
parser.add_argument(
    "-b", "--browser",
    default="",
    help="Specifikovat WebDriver prohlížeče, který použít"
)
parser.add_argument(
    "-e", "--executablePath",
    default=None,
    help="Cesta ke spustitelnému webdriveru pro prohlížeč, který je specifikovaný pomocí '-b'"
)
parser.add_argument(
    "-t", "--test",
    type=int,
    default=-1,
    help="Test, který se má spustit (funguje pouze v kombinaci s '--shell')"
)
parser.add_argument(
    "-n", "--no-auto-run",
    help="Pokud je tato flaga přítomna, nespustí se žádné automatické akce kromě přihlášení",
    action="store_true"
)
args = parser.parse_args()

url = args.url
user = args.jmeno
password = args.heslo
testToRun = args.test
noAutoRun = args.no_auto_run

seleniumSettings: bakalariapi.SeleniumHandler | None = None
if args.browser != "":
    seleniumSettings = bakalariapi.SeleniumHandler(bakalariapi.Browser[args.browser.upper()], args.executablePath)

def cls():
    os.system('cls' if os.name=='nt' else 'clear')
def AnoNeDialog(text: str = "", default: bool | None = None) -> bool:
    while True:
        inpt = input(f"{text} Ano/Ne{'' if default is None else (' (Ano)' if default else ' (Ne)')}: ") # ano/true/yes/1 / ne/false/no/0
        if len(inpt) == 0:
            if default is None:
                continue
            return default
        input_letter = inpt[0].lower()
        if input_letter in "aty1":
            return True
        if input_letter in "nf0":
            return False
def InputCislo(text: str = "", default: int | None = None):
    while True:
        inpt = input(text + ("" if default is None else f" ({default})"))
        if not inpt:
            if default is None:
                continue
            return default
        if inpt.isdecimal():
            return int(inpt)
        print("Špatná hodnota")

API: bakalariapi.BakalariAPI = bakalariapi.BakalariAPI(url, user, password, seleniumSettings)

def Login():
    global API

    print(f"Kontrola stavu serveru/webu... ({url})")
    if not API.is_server_running():
        print("Severver/web (pravděpodobně) neběží; Končím")
        exit(1)
    print("Sever/web běží")
    print(f"Kontrola přihlašovacích údajů pro uživatele '{user}'")
    if not API.is_login_valid():
        print("Přihlašovací údaje jsou neplatné")
    print("Přihlašovací údaje ověřeny a jsou správné")
    print("Nastavuji...")
    API.init()
    print("Nastaveno:")
    ServerInfo()
def ServerInfo():
    print(
        f"Typ uživatele: {API.user_info.type}\n"
        f"Uživatelký hash: {API.user_info.hash}\n"
        f"Verze Bakalářů: {API.server_info.version}\n"
        f"Datum verze Bakalářů: {API.server_info.version_date.strftime('%d. %m. %Y')}\n"
        f"Evidenční číslo verze Bakalářů: {API.server_info.evid_number}"
    )
    if API.server_info.version != bakalariapi.LAST_SUPPORTED_VERSION:
        print("*** Jiná verze Bakalářů! Všechny funkce nemusejí fungovat správně! ***")
def Komens(limit: int | None = None):
    print("Získávám zprávy...")
    zpravy = API.get_fresh_komens(limit=limit)
    length = len(zpravy)
    print(f"Zprávy získány ({length}), zobrazuji...")
    cls()
    count = 1
    for zprava in zpravy:
        try:
            print(f"*** Zpráva {count} z {length} ***")
            print(zprava.format())
            print("\n\n\n")
            if zprava.need_confirm and not zprava.confirmed and AnoNeDialog("Zpráva vyžaduje potvrzení. Chcete potvrdit přečtení?"):
                print("Potvrzuji zprávu...")
                zprava.confirm(API)
                print("Zpráva potvrzena")
            count += 1
            input("Pro pokračování stiskni klávasu...")
            cls()
        except KeyboardInterrupt:
            print("\n")
            break
def Znamky():
    print("Získávám známky...")
    znamky = API.get_fresh_grades()
    length = len(znamky)
    print(f"Známky získány ({length}), zobrazuji...")
    cls()
    count = 1
    for znamka in znamky:
        try:
            print(f"*** Známka {count} z {length} ***")
            print(znamka.format())
            print("\n")
            count += 1
            input("Pro pokračování stiskni klávasu...")
            cls()
        except KeyboardInterrupt:
            print("\n")
            break
def Schuzky():
    print("Získávám online schůzky...")
    schuzky = API.get_fresh_meetings_future()
    length = len(schuzky)
    print(f"Online schůzky získány ({length}), zobrazuji...")
    cls()
    count = 1
    for schuzka in schuzky:
        try:
            print(f"*** Online Schůzka {count} z {length} ***")
            print(schuzka.format())
            print("\n\n")
            diff = schuzka.start_time - datetime.now(timezone.utc)
            if diff <= timedelta(minutes=30) and AnoNeDialog("Chcete otevřít online schůzku? Shůzka začíná do 30ti minut...", False):
                print("Otevírám...")
                webbrowser.open_new_tab(schuzka.joinURL)
            count += 1
            input("Pro pokračování stiskni klávasu...")
            cls()
        except KeyboardInterrupt:
            print("\n")
            break
def Studenti():
    print("Získávám studenty...")
    studenti = API.get_fresh_students()
    length = len(studenti)
    print(f"Studenti získáni, počet studentů je {length}")
    count = InputCislo("Kolik zobrazit výsledků najednou? (Výchozí 25) ", 25)
    offset = 0
    cls()
    while offset < length:
        try:
            for _ in range(count):
                if (offset >= length):
                    break
                print(studenti[offset].format())
                offset += 1
            input(f"Pro pokračování stiskni klávasu... (Již zobrazeno {offset} výsledků z {length})")
            cls()
        except KeyboardInterrupt:
            print("\n")
            break
def Konec(nice: bool = True):
    global shell_instance
    API.kill(nice)
    shell_instance.stop_loop()
def Ukoly(fast: bool = False):
    print("Načítání úkolů...")
    if fast:
        ukoly = API.get_fresh_homeworks_fast()
    else:
        ukoly = API.get_fresh_homeworks_slow(False, False)

    length = len(ukoly)
    print(f"Úkoly načteny ({length})")
    zobraz_hotove = fast or AnoNeDialog("Chte zobrazit již hotové úkoly?")
    cls()
    count = 1
    for ukol in ukoly:
        try:
            if not zobraz_hotove and ukol.done:
                continue
            print(f"*** Domácí úkol {count} z {length} ***")
            print(ukol.format())
            print("\n\n")
            if not ukol.done and AnoNeDialog("Úkol není označen jako hotov... Chcete ho označit jako hotový?", False):
                ukol.mark_as_done(API)
                print("Úkol byl označen jako hotový")
            count += 1
            input("Pro pokračování stiskni klávasu...")
            cls()
        except KeyboardInterrupt:
            print("\n")
            break

def RunTest(id: int):
    m = __import__(__name__)
    t = f"Test{id}"
    if hasattr(m, t):
        print(f"Zahajuji test {id}")
        try:
            o = getattr(m, t)()
            print(f"Test {id} skončil" + ("" if o is None else f"; Výsledek testu je {o}"))
        except:
            print("Test skončil neúspěchem:")
            traceback.print_exc()
    else:
        print(f"Test {id} nenalezen")
def Test0():
    print("Spouštím testování...")
    try:
        while True:
            session = API.session_manager.get_session(bakalariapi.RequestsSession)
            last = session.get(API.get_endpoint(Endpoint.SESSION_INFO)).json()["data"]["remainingTime"]
            print("\r", end="")
            while True:
                print("Současný zbývající čas: " + str(last) + " "*20, end="\r") #Some spaces to rewrite previous text...
                session.get(API.get_endpoint(Endpoint.SESSION_EXTEND))
                current = float(session.get(API.get_endpoint(Endpoint.SESSION_INFO)).json()["data"]["remainingTime"])
                if last < current:
                    print("\n")
                    break
                last = current
                time.sleep(1)
            print("Sezení bylo prodlouženo, když zbývalo " + str(last) + " (+ max 1s) do konce a bylo prodlouženo na " + str(current))
    except KeyboardInterrupt:
        print("Testování ukončeno")
def Test1():
    #Získáme si nějká data...
    # print("Získáváme data (schůzky + studenti)...")
    # API.get_fresh_meetings_future()
    # print("Data získána")

    #"Kopírování"
    print("Vytváření kopie skrz JSON export/import...")
    new = bakalariapi.Looting()
    json = API.looting.export_JSON()
    print(json)
    new.import_JSON(json)
    print("Kopie vytvořena")

    #Porovnávání
    typ_mismatch = 0
    id_len_mismatch = 0
    id_mismatch = 0
    print("=" * 30)
    print(f"Počet typů v datech (old): {len(API.looting.data)}")
    print(f"Počet typů v datech (new): {len(API.looting.data)}")
    print("Porovnávání zahájeno...")
    for typ_old, typ_new in zip(API.looting.data.keys(), new.data.keys()):
        if typ_old != typ_new:
            print(f"Neshodující se typy! Old: '{typ_old}'; New: '{typ_new}'")
            typ_mismatch += 1
            continue
        old_id_len = len(API.looting.data[typ_old])
        new_id_len = len(new.data[typ_new])
        if old_id_len != new_id_len:
            print(f"Neshodující se počet záznamů pro typ {typ_old}! Old: {old_id_len}; New: {new_id_len}")
            id_len_mismatch += 1
        for id_old, obj_old, id_new, obj_new in zip(API.looting.data[typ_old].keys(), API.looting.data[typ_old].values(), new.data[typ_new].keys(), new.data[typ_new].values()):
            if id_old != id_new:
                print(f"Neshodující se ID! Old: '{id_old}'; New: '{id_new}' (typ: {typ_old}; ID type (old): {type(id_old)}; ID type (new): {type(id_new)})")
                id_mismatch += 1
    
    print(f"Porovnávání dokončeno:\nChyb u typů:\t{typ_mismatch}\nChyb u ID:\t{id_mismatch}")
    return (typ_mismatch, id_mismatch, id_len_mismatch)
def Test2():
    print("Tento test již není podporován... Sadge")
    return
    print("Získávám IDčka online schůzek")
    IDs = API.GetAllMeetingsIDs()
    print("IDčka online schůzek získany")
    for ID in IDs:
        print(f"Získávám online schůzku {ID}")
        if API.GetMeeting(ID) is None:
            print(f"Online schůzku {ID} se nepodařilo načíst")
        else:
            print(f"Online schůzka {ID} byla načtena")
def Test3():
    print("Tento test již není podporován... Sadge")
    return
    return API.GetHomeworksIDs()
def Test4():
    print("Tento test již není podporován... Sadge")
    return
    print("Test byl přestal být podporován a byl zrušen...")
    #return API.MarkHomeworkAsDone(input("ID Úkolu: "), input("ID Studenta: "), True)
def Test5():
    print("Tento test již není podporován... Sadge")
    return
    homeworks = API.GetHomeworks()
    print("Úkoly načteny...")
    zobrazHotove = AnoNeDialog("Chte zobrazit již hotové úkoly?")
    cls()
    for homework in homeworks:
        if not zobrazHotove and homework.Done:
            continue
        print("*** Domácí úkol ***")
        print(homework.Format())
        print("\n\n")
        input("Pro pokračování stiskni klávasu...")
        cls()
def Test6():
    count_total = 0
    count_invalid = 0
    try:
        while True:
            count_total += 1
            output = API.get_fresh_homeworks_slow(False, False)
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


Login()

if not noAutoRun:
    pass

print()
print("Shell aktivní")
shell_instance = shell.Shell(
    prompt="BakalariAPI Shell>",
    allow_python_exec=True,
    python_exec_prefix=" ",
    python_exec_globals=globals(),
    python_exec_locals=locals(),
    generate_commands=["help", "prompt"]
)
shell_instance.add_command(shell.Command(
    "clear",
    cls,
    short_help="Vyčistí konzoli/terminál",
    aliases=["cls"]
))
parser = shell.ShellArgumentParser()
parser.add_argument("limit", type=int, nargs="?", default=None, help="Limituje počet zpráv, které se načtou a tím i zrychlí proces")
shell_instance.add_command(shell.Command(
    "komens",
    Komens,
    short_help="Extrahuje a zobrazí komens zprávy",
    argparser=parser,
    spread_arguments=True,
    aliases=["zpravy", "zprávy"]
))
shell_instance.add_command(shell.Command(
    "znamky",
    Znamky,
    short_help="Extrahuje a zobrazí známky"
))
shell_instance.add_command(shell.Command(
    "schuzky",
    Schuzky,
    short_help="Extrahuje a zobrazí (nadcházející) schůzky"
))
shell_instance.add_command(shell.Command(
    "studenti",
    Studenti,
    short_help="Zobrazí studenty"
))
parser = shell.ShellArgumentParser()
parser.add_argument("id", help="ID testu, který se má spustit")
shell_instance.add_command(shell.Command(
    "test",
    RunTest,
    argparser=parser,
    short_help="Spustí daný test",
    spread_arguments=True
))
parser = shell.ShellArgumentParser()
parser.add_argument(
    "-f", "--fast",
    help="Pokud je tato flaga přítomna, úkoly budou získány v 'rychlém módu'",
    action="store_true",
    default=False
)
shell_instance.add_command(shell.Command(
    "ukoly",
    Ukoly,
    argparser=parser,
    short_help="Zobrazí úkoly",
    aliases=["úkoly"],
    spread_arguments=True,
))
shell_instance.add_command(shell.Command(
    "server",
    ServerInfo,
    short_help="Zobrazí informace o serveru",
))
parser = shell.ShellArgumentParser()
parser.add_argument(
    "-f", "--force",
    help="Pokud je tato flaga přítomna, neprovede se odlášení sessionů a aplikace se tedy rychleji ukončí",
    action="store_false",
    default=True,
    dest="nice"
)
shell_instance.add_command(shell.Command(
    "exit",
    Konec,
    argparser=parser,
    short_help="Ukončí shell",
    spread_arguments=True,
))

if testToRun != -1:
    RunTest(testToRun)
shell_instance.start_loop()
