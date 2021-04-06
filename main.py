import argparse
import os
import bakalari
import shell
from datetime import datetime, timedelta, timezone # Here it comes... Timezone hadndling first feel PepeLaugh
# Hej! Moje budoucí já... Já vím, že se sem jednou podíváš... Takže až ta chvíle nastane, tak si vzpomeň, že za 100 let budou tenhle samej problém
# s časovými pásmy řešit furt :) Takže nevadí, že si to pořád ještě po 10h debugu nespravil...
# HA! Dělám si srandu. Padej to opravit! S láskou - Tvoje minulé já :)
import webbrowser
import time
import multiprocessing

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

seleniumSettings: bakalari.SeleniumHandler = None
if args.browser != "":
    seleniumSettings = bakalari.SeleniumHandler(bakalari.Browser[args.browser.upper()], args.executablePath)

def cls():
    os.system('cls' if os.name=='nt' else 'clear')
def AnoNeDialog(text: str = "", help_text: bool = True) -> bool:
    while True:
        input_letter = input(text + ("Ano/Ne: " if help_text else "")) # ano/yes/1 / ne/no/0
        if len(input_letter) == 0:
            continue
        input_letter = input_letter[0].lower()
        if input_letter in "ay1":
            return True
        elif input_letter in "n0":
            return False
        print("Špatná hodnota")
def InputCislo(text: str = "", default: int = None):
    while True:
        inpt = input(text)
        if not inpt and default != None:
            return default
        if inpt.isdecimal():
            return int(inpt)
        print("Špatná hodnota")

API: bakalari.BakalariAPI = bakalari.BakalariAPI(url, user, password, seleniumSettings)

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
    print("Nastaveno")
    ServerInfo()
    input("Pro pokračování stiskni klávasu...")
def ServerInfo():
    print(
        f"  Typ uživatele: {API.user_info.type}\n"
        f"  Uživatelký hash: {API.user_info.hash}\n"
        f"  Verze Bakalářů: {API.server_info.version}\n"
        f"  Datum verze Bakalářů: {API.server_info.version_date.strftime('%d. %m. %Y')}\n"
        f"  Evidenční číslo verze Bakalářů: {API.server_info.evid_number}\n"
    )
    if API.server_info.version != bakalari.LAST_SUPPORTED_VERSION:
        print("*** Jiná verze Bakalářů! Všechny funkce nemusejí fungovat správně! ***")
def Komens():
    print("Získávám zprávy...")
    zpravy = API.get_fresh_komens()
    length = len(zpravy)
    print(f"Zprávy získány ({length}), zobrazuji...")
    cls()
    count = 1
    for zprava in zpravy:
        try:
            print(f"*** Zpráva {count} z {length} ***")
            print(zprava.format())
            print("\n\n\n")
            if zprava.need_confirm and not zprava.confirmed and AnoNeDialog("Zpráva vyžaduje potvrzení. Chcete potvrdit přečtení? "):
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
            diff = schuzka.start_time - datetime.now(timezone.utc).astimezone()
            if diff <= timedelta(minutes=30) and AnoNeDialog("Chcete otevřít online schůzku? Shůzka začíná do 30ti minut... "):
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
def Konec():
    API.kill()
def Ukoly():
    print("Načítání úkolů...")
    ukoly = API.get_fresh_homeworks_slow(False, False)
    length = len(ukoly)
    print(f"Úkoly načteny ({length})")
    zobraz_hotove = AnoNeDialog("Chte zobrazit již hotové úkoly? ")
    cls()
    count = 1
    for ukol in ukoly:
        try:
            if not zobraz_hotove and ukol.done:
                continue
            print(f"*** Domácí úkol {count} z {length} ***")
            print(ukol.format())
            print("\n\n")
            if not ukol.done and AnoNeDialog("Úkol není označen jako hotov... Chcete ho označit jako hotový? "):
                ukol.mark_as_done(API)
                print("Úkol byl označen jako hotový")
            count += 1
            input("Pro pokračování stiskni klávasu...")
            cls()
        except KeyboardInterrupt:
            print("\n")
            break

#TODO: Obnovit některé testy...
def RunTest(id):
    m = __import__(__name__)
    t = f"Test{id}"
    if hasattr(m, t):
        print(f"Zahajuji test {id}")
        o = getattr(m, t)()
        print(f"Test {id} skončil; Výsledek testu je {o}")
    else:
        print(f"Test {id} nenalezen")
def Test0():
    print("Tento test již není podporován... Sadge")
    return
    print("Spouštím testování...")
    while True:
        last = API.Session.get(API.Server.GetEndpoint("session_info")).json()["data"]["remainingTime"]
        print("\r", end="")
        while True:
            print("Současný zbývající čas: " + str(last) + "                       ", end="\r") #Some spaces to rewrite previous text...
            API.Session.get(API.Server.GetEndpoint("session_extend"))
            current = float(API.Session.get(API.Server.GetEndpoint("session_info")).json()["data"]["remainingTime"])
            if last < current:
                print("\n")
            break
            last = current
            time.sleep(1)
        print("Sezení bylo prodlouženo, když zbývalo " + str(last) + " (+ max 1s) do konce a bylo prodlouženo na " + str(current))
def Test1():
    print("Tento test již není podporován... Sadge")
    return
    # schuzkyIDs = API.GetMeetingsIDs()
    # print("IDčka online schůzek získany")
    # for ID in schuzkyIDs:
    #     print(f"Získávám online chůzku {ID}")
    #     API.GetMeeting(ID)
    # originalStudentLen = len(BakalariAPI.Looting.Data["Student"])
    # randomStudentIndex = 10 # Ano, náhodný... Extrémně se mi nechce ještě teď po zprovoznění deseralizace lootingu něco hledat...
    # randomStudentOriginalName = BakalariAPI.Looting.Data["Student"][randomStudentIndex].Name + " " + BakalariAPI.Looting.Data["Student"][randomStudentIndex].Surname
    string = API.Loot.ToJSON()

    API.Loot.Data = {}
    API.Loot.IDs = {}

    API.Loot.FromJSON(string)
    # currentStudentLen = len(BakalariAPI.Looting.Data["Student"])
    # randomStudentCurrentName = BakalariAPI.Looting.Data["Student"][randomStudentIndex].Name + " " + BakalariAPI.Looting.Data["Student"][randomStudentIndex].Surname
    # if currentStudentLen == originalStudentLen:
    #     print(f"Počet studentů je shodný ({originalStudentLen})")
    # else:
    #     print(f"Počet studentů se liší ({originalStudentLen}; {currentStudentLen})")
    # if randomStudentOriginalName == randomStudentCurrentName:
    #     print(f"Jméno náhodného studenta je stejný ({randomStudentOriginalName})")
    # else:
    #     print(f"Jméno náhodného studenta se liší ({randomStudentOriginalName}; {randomStudentCurrentName})")
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
    zobrazHotove = AnoNeDialog("Chte zobrazit již hotové úkoly? ")
    cls()
    for homework in homeworks:
        if not zobrazHotove and homework.Done:
            continue
        print("*** Domácí úkol ***")
        print(homework.Format())
        print("\n\n")
        input("Pro pokračování stiskni klávasu...")
        cls()


Login()

if not noAutoRun:
    pass

cls()
print("Shell aktivní")
shell_instance = shell.Shell(
    prompt="BakalariAPI Shell>",
    allow_python_exec=True,
    python_exec_prefix=" ",
    python_exec_globals=globals(),
    python_exec_locals=locals()
)
shell_instance.add_command(shell.Command(
    "clear",
    cls,
    short_help="Vyčistí konzoli/terminál",
    aliases=["cls"]
))
shell_instance.add_command(shell.Command(
    "komens",
    Komens,
    short_help="Extrahuje a zobrazí komens zprávy"
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
parser.add_argument("id")
shell_instance.add_command(shell.Command(
    "test",
    RunTest,
    parser,
    "Spustí daný test (současně jsou všechny test zastaralé a nespustí se)",
    spread_arguments=True
))
shell_instance.add_command(shell.Command(
    "ukoly",
    Ukoly,
    short_help="Zobrazí úkoly",
    aliases=["úkoly"]
))
shell_instance.add_command(shell.Command(
    "server",
    ServerInfo,
    short_help="Zobrazí informace o serveru",
))

if testToRun != -1:
    RunTest(testToRun)
shell_instance.start_loop()
Konec()
