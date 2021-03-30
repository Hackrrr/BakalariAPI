import argparse
import os
import requests
from bakalari import BakalariAPI, LAST_SUPPORTED_VERSION, Browser, SeleniumHandler
import Shell
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

seleniumSettings: SeleniumHandler = None
if args.browser != "":
    seleniumSettings = SeleniumHandler(Browser[args.browser.upper()], args.executablePath)

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

API: BakalariAPI = BakalariAPI(url, user, password, seleniumSettings)

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
    if API.server_info.version != LAST_SUPPORTED_VERSION:
        print("*** Jiná verze Bakalářů! Všechny funkce nemusejí fungovat správně! ***")
def Komens():
    print("Získávám IDčka zpráv...")
    zpravyIDs = API.get_komens_IDs()
    zpravy = []
    print("IDčka zpráv získany")
    for ID in zpravyIDs:
        print(f"Získávám Komens zprávu {ID}")
        zpravy.append(API.get_komens(ID))
    print("Zprávy získány, zobrazuji...")
    cls()
    for zprava in zpravy:
        print("*** Zpráva ***")
        print(zprava.format())
        print("\n\n\n")
        if zprava.need_confirm and not zprava.confirmed and AnoNeDialog("Zpráva vyžaduje potvrzení. Chcete potvrdit přečtení? "):
            print("Potvrzuji zprávu...")
            zprava.confirm(API)
            print("Zpráva potvrzena")
        input("Pro pokračování stiskni klávasu...")
        cls()
def Znamky():
    print("Získávám známky...")
    znamky = API.get_grades()
    print("Známky získány, zobrazuji...")
    cls()
    for znamka in znamky:
        print("*** Známka ***")
        print(znamka.format())
        print("\n")
        input("Pro pokračování stiskni klávasu...")
        cls()
def Schuzky():
    print("Získávám IDčka online schůzek")
    schuzkyIDs = API.get_future_meetings_IDs()
    print("IDčka online schůzek získany")
    schuzky = []
    for ID in schuzkyIDs:
        print(f"Získávám online schůzku {ID}")
        schuzky.append(API.get_meeting(ID))
    print("Online schůzky získány, zobrazuji...")
    cls()
    for schuzka in schuzky:
        print("*** Online Schůzka ***")
        print(schuzka.format())
        print("\n\n")
        diff = schuzka.start_time - datetime.now(timezone.utc).astimezone()
        if diff <= timedelta(minutes=30) and AnoNeDialog("Chcete otevřít online schůzku? Shůzka začíná do 30ti minut... "):
            print("Otevírám...")
            webbrowser.open_new_tab(schuzka.joinURL)
        input("Pro pokračování stiskni klávasu...")
        cls()
def Studenti():
    if len(API.looting.data["Student"]) and AnoNeDialog("Podařilo získat seznam studentů. Chcete jej zobrazit? "):
        count = InputCislo("Kolik výsledků najednou? (Výchozí 25) ", 25)
        offset = 0
        length = len(API.looting.data["Student"])
        cls()
        while offset < length:
            for _ in range(count):
                if (offset >= length):
                    break
                print(API.looting.data["Student"][offset].format())
                offset += 1
            input(f"Pro pokračování stiskni klávasu... (Již zobrazeno {offset} výsledků z {length})")
            cls()
def Konec():
    API.kill()
def Ukoly():
    # print("Vytvářím Selenium session...")
    # driver = API.Selenium_Create()
    # print(f"Selenium session vytvořen, přihlašuji jako {user}... (Session ID: {driver.session_id})")
    # if not API.Selenium_Login(driver):
    #     print("Zdá se, že přihlášení přes Selenium session se nezdařilo... Jsou správně přihlašovací údaje?")
    # print("Úspěšně přihlášen přes Selenium session")
    print("Načítání úkolů...")
    homeworks = API.get_homeworks(False)
    print("Úkoly načteny")
    zobrazHotove = AnoNeDialog("Chte zobrazit již hotové úkoly? ")
    cls()
    for homework in homeworks:
        if not zobrazHotove and homework.done:
            continue
        print("*** Domácí úkol ***")
        print(homework.format())
        print("\n\n")
        if not homework.done and AnoNeDialog("Úkol není označen jako hotov... Chcete ho označit jako hotový? "):
            homework.mark_as_done(API)
            print("Úkol byl označen jako hotový")
        input("Pro pokračování stiskni klávasu...")
        cls()

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
    print("Spouštím testování...")
    while True:
        last = API.Session.get(API.Server.GetEndpoint("session_info")).json()["data"]["remainingTime"]
        print("\r", end="")
        while True:
            print("Současný zbývající čas: " + str(last) + "                       ", end="\r") #Some spaces to rewrite previous text...
            API.Session.get(API.Server.GetEndpoint("session_extend"))
            current = float(API.Session.get(API.Server.GetEndpoint("session_info")).json()["data"]["remainingTime"])
            if last < current:
                break
            last = current
            time.sleep(1)
        print("Sezení bylo prodlouženo, když zbývalo " + str(last) + " (+ max 1s) do konce a bylo prodlouženo na " + str(current))
def Test1():
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
    return API.GetHomeworksIDs()
def Test4():
    print("Test byl přestal být podporován a byl zrušen...")
    #return API.MarkHomeworkAsDone(input("ID Úkolu: "), input("ID Studenta: "), True)
def Test5():
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

if (not noAutoRun):
    pass

cls()
print("Shell aktivní")
shell = Shell.Shell(
    "BakalariAPI Shell>",
    allowPythonExec=True,
    pythonExecPrefix=" "
)
shell.AddCommand(Shell.Command(
    "clear",
    cls,
    shortHelp="Vyčistí konzoli/terminál",
    aliases=["cls"]
))
shell.AddCommand(Shell.Command(
    "komens",
    Komens,
    shortHelp="Extrahuje a zobrazí komens zprávy"
))
shell.AddCommand(Shell.Command(
    "znamky",
    Znamky,
    shortHelp="Extrahuje a zobrazí známky"
))
shell.AddCommand(Shell.Command(
    "schuzky",
    Schuzky,
    shortHelp="Extrahuje a zobrazí (nadcházející) schůzky"
))
shell.AddCommand(Shell.Command(
    "studenti",
    Studenti,
    shortHelp="Zobrazí studenty"
))
parser = Shell.ShellArgumentParser()
parser.add_argument("id")
shell.AddCommand(Shell.Command(
    "test",
    RunTest,
    parser,
    "Spustí daný test",
    spreadArguments=True
))
shell.AddCommand(Shell.Command(
    "ukoly",
    Ukoly,
    shortHelp="Zobrazí úkoly",
    aliases=["úkoly"]
))
shell.AddCommand(Shell.Command(
    "server",
    ServerInfo,
    shortHelp="Zobrazí informace o serveru",
))

if testToRun != -1:
    RunTest(testToRun)
shell.StartLoop()
Konec()
