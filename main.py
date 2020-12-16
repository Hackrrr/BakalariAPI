import argparse
import os
import requests
import BakalariAPI
import Shell
from datetime import datetime, timedelta, timezone # Here it comes... Timezone hadndling first feel PepeLaugh
# Hej! Moje budoucí já... Já vím, že se sem jednou podíváš... Takže až ta chvíle nastane, tak si vzpomeň, že za 100 let budou tenhle samej problém
# s časovými pásmy řešit furt :) Takže nevadí, že si to pořád ještě po 10h debugu nespravil...
# HA! Dělám si srandu. Padej to opravit! S láskou - Tvoje minulé já :)
import webbrowser
import time

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
    "-i", "--interactive",
    default=False,
    action="store_true",
    help="Interaktivní - Vyžaduje interakci po zobrazení zprávy/známky/..."
)
parser.add_argument(
    "-s", "--shell",
    default=False,
    action="store_true",
    help="Spusť BakalariAPI shell (velmi se doporučuje skombinovat s '--interactive')"
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
args = parser.parse_args()

url = args.url
user = args.jmeno
password = args.heslo
interactive = args.interactive
shell = args.shell
testToRun = args.test

seleniumSettings: BakalariAPI.SeleniumHandler = None
if args.browser != "":
    if args.browser not in BakalariAPI.Browser.__members__:
        raise BakalariAPI.InputException(f"Prohlížeč '{args.browser}' nelze použít")
    seleniumSettings = BakalariAPI.SeleniumHandler(BakalariAPI.Browser[args.browser], args.executablePath)

def cls():
    os.system('cls' if os.name=='nt' else 'clear')
def AnoNeDialog(text: str = "", help: bool = True) -> bool:
    while True:
        inputLetter = input(text + ("Ano/Ne: " if help else "")) # ano/yes/1 / ne/no/0
        if len(inputLetter) == 0:
            continue
        inputLetter = inputLetter[0].lower()
        if inputLetter in "ay1":
            return True
        elif inputLetter in "n0":
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

API: BakalariAPI.BakalariAPI = None

def Login():
    global API
    try:
        API = BakalariAPI.BakalariAPI(
            BakalariAPI.Server(url),
            user,
            password,
            False,
            True,
            seleniumSettings
        )
    except BakalariAPI.InputException:
        print("Neplatné URL schéma; Končím")
        exit(1)
    print(f"Kontrola stavu serveru/webu... ({url})")
    if not API.Server.Running():
        print("Severver/web (pravděpodobně) neběží; Končím")
        exit(1)
    print("Sever/web běží")
    print(f"Pokus o přihlášení jako '{user}'")
    try:
        API.Login(False)
    except BakalariAPI.AuthenticationException:
        print("Nepovedlo se přihlásit (nesprávné přihlašovací údaje)")
        exit(1)
    print("Přihlášení úspěšné")

    print("Nastavuji...")
    API.Init()
    print("Nastaveno")
    print(
        "Základní informace:\n"
        f"  Typ uživatele: {API.UserType}\n"
        f"  Uživatelký hash: {API.UserHash}\n"
        f"  Verze Bakalářů: {API.Server.Version}\n"
        f"  Datum verze Bakalářů: {API.Server.VersionDate.strftime('%d. %m. %Y')}\n"
        f"  Evidenční číslo verze Bakalářů: {API.Server.RegistrationNumber}\n"
    )
    if API.Server.Version != BakalariAPI.LAST_SUPPORTED_VERSION:
        print("*** Jiná verze Bakalářů! Všechny funkce nemusejí fungovat správně! ***")
    if interactive:
        input("Pro pokračování stiskni klávasu...")
def Komens():
    print("Získávám IDčka zpráv...")
    zpravyIDs = API.GetKomensIDs()
    zpravy = []
    print("IDčka zpráv získany")
    for ID in zpravyIDs:
        print(f"Získávám Komens zprávu {ID}")
        zpravy.append(API.GetKomens(ID))
    print("Zprávy získány, zobrazuji...")
    if interactive:
        cls()
    for zprava in zpravy:
        # try:
        print("*** Zpráva ***")
        print(zprava.Format())
        print("\n\n\n")
        if interactive:
            if zprava.NeedsConfirm and not zprava.Confirmed and AnoNeDialog("Zpráva vyžaduje potvrzení. Chcete potvrdit přečtení? "):
                print("Potvrzuji zprávu...")
                zprava.Confirm()
                print("Zpráva potvrzena")
            input("Pro pokračování stiskni klávasu...")
            cls()
def Znamky():
    print("Získávám známky...")
    znamky = API.GetGrades()
    print("Známky získány, zobrazuji...")
    if interactive:
        cls()
    for znamka in znamky:
        print("*** Známka ***")
        print(znamka.Format())
        print("\n")
        if interactive:
            input("Pro pokračování stiskni klávasu...")
            cls()
def Schuzky():
    print("Získávám IDčka online schůzek")
    schuzkyIDs = API.GetMeetingsIDs()
    print("IDčka online schůzek získany")
    schuzky = []
    for ID in schuzkyIDs:
        print(f"Získávám online schůzku {ID}")
        schuzky.append(API.GetMeeting(ID))
    print("Online schůzky získány, zobrazuji...")
    if interactive:
        cls()
    for schuzka in schuzky:
        print("*** Online Schůzka ***")
        print(schuzka.Format())
        print("\n\n")
        if interactive:
            diff = schuzka.StartTime - datetime.now(timezone.utc).astimezone()
            if diff <= timedelta(minutes=30) and AnoNeDialog(f"Chcete otevřít online schůzku? Shůzka začíná do 30ti minut... "):
                print("Otevírám...")
                webbrowser.open_new_tab(schuzka.JoinURL)
            input("Pro pokračování stiskni klávasu...")
            cls()
def Studenti():
    if interactive and len(API.Loot.Data["Student"]) and AnoNeDialog("Podařilo získat seznam studentů. Chcete jej zobrazit? "):
        count = InputCislo("Kolik výsledků najednou? (Výchozí 25) ", 25)
        offset = 0
        length = len(API.Loot.Data["Student"])
        cls()
        while offset < length:
            for _ in range(count):
                if (offset >= length):
                    break
                print(API.Loot.Data["Student"][offset].Format())
                offset += 1
            input(f"Pro pokračování stiskni klávasu... (Již zobrazeno {offset} výsledků z {length})")
            cls()
def Konec():
    API.Logout()
def Ukoly():
    print("Vytvářím Selenium session...")
    driver = API.Selenium_Create()
    print(f"Selenium session vytvořen, přihlašuji jako {user}... (Session ID: {driver.session_id}")
    if not API.Selenium_Login(driver):
        print("Zdá se, že přihlášení přes Selenium session se nezdařilo... Jsou správně přihlašovací údaje?")
    print("Úspěšně přihlášen přes Selenium session")
    print("Načítání úkolů...")
    homeworks = API.GetHomeworks(driver=driver)
    print("Úkoly načteny")
    if interactive:
        zobrazHotove = AnoNeDialog("Chte zobrazit již hotové úkoly? ")
        cls()
    for homework in homeworks:
        if interactive and not zobrazHotove and homework.Done:
            continue
        print("*** Domácí úkol ***")
        print(homework.Format())
        print("\n\n")
        if interactive:
            if not homework.Done and AnoNeDialog("Úkol není označen jako hotov... Chcete ho označit jako hotový? "):
                homework.MarkAsDone(API)
                print("Úkol byl označen jako hotový")
            input("Pro pokračování stiskni klávasu...")
            cls()
    driver.close()

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
        if API.GetMeeting(ID) == None:
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

if shell:
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

    if testToRun != -1:
        RunTest(testToRun)
    shell.StartLoop()
    Konec()
    exit(0)

Komens()
Znamky()
Schuzky()
Studenti()
Ukoly()
Konec()