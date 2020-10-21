import argparse
import os
import requests
import BakalariAPI
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
# parser.add_argument(
#     "-t", "--test",
#     default=False,
#     action="store_true",
#     help="Test snippet"
# )
# parser.add_argument(
#     "-d", "--debug",
#     default=False,
#     action="store_true",
#     help="Možnost debug konzole v běhu"
# )
args = parser.parse_args()

url = args.url
user = args.jmeno
password = args.heslo
interactive = args.interactive
shell = args.shell


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
def DebugMode():
    try:
        while True:
            try:
                exec("print(" + input() + ")")
            except KeyboardInterrupt:
                raise KeyboardInterrupt
            except Exception as e:
                print(e)
    except KeyboardInterrupt:
        return
def Shell():
    """Dočasné řešení interaktivity
    Nespoléhat se na tohle - Bude se mazat nebo kompletně přepisovat na něco komplexnějšího...
    """
    cls()
    print("Shell aktivní")
    while True:
        try:
            print("BakalariAPI shell> ", end="")
            inpt = input()
            if len(inpt) == 0:
                continue
            if "help".startswith(inpt.lower()) or inpt == "?":
                print("%-15s %s" % ("komens",   "Zobrazuje komens zprávy"))
                print("%-15s %s" % ("schuzky",  "Zobrazuje online schůzky"))
                print("%-15s %s" % ("studenti", "Zobrazuje studenty"))
                print("%-15s %s" % ("znamky",   "Zobrazuje známky"))
                print("%-15s %s" % ("help",     "Zobrazuje (tuto) nápovědu"))
                print("%-15s %s" % ("?",        "Zobrazuje (tuto) nápovědu"))
                print("%-15s %s" % ("exit",     "Ukončí aplikaci"))
                print("%-15s %s" % ("konec",    "Ukončí aplikaci"))
                print("%-15s %s" % ("testX",    "Spustí testovací snippet s číslem X"))
            elif "komens".startswith(inpt.lower()):
                Komens()
            elif "schuzky".startswith(inpt.lower()):
                Schuzky()
            elif "student".startswith(inpt.lower()):
                Studenti()
            elif "znamky".startswith(inpt.lower()):
                Znamky()
            elif "exit".startswith(inpt.lower()) or "help".startswith(inpt.lower()):
                Konec()
                exit(0)
            elif "test".startswith(inpt[:-1].lower()):
                getattr(__import__(__name__), f"Test{inpt[-1]}")()
            else:
                try:
                    exec(f"print({inpt})")
                except Exception as e:
                    print(e)
            
        except KeyboardInterrupt:
            exit(0)


API = None

def Login():
    global API
    try:
        API = BakalariAPI.BakalariAPI(
            BakalariAPI.Server(url),
            user,
            password,
            False
        )
    except BakalariAPI.Exceptions.InputException:
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
    except BakalariAPI.Exceptions.AuthenticationException:
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
    if interactive and len(BakalariAPI.Looting.Data["Student"]) and AnoNeDialog("Podařilo získat seznam studentů. Chcete jej zobrazit? "):
        count = InputCislo("Kolik výsledků najednou? (Výchozí 25) ", 25)
        offset = 0
        length = len(BakalariAPI.Looting.Data["Student"])
        cls()
        while offset < length:
            for _ in range(count):
                if (offset >= length):
                    break
                print(BakalariAPI.Looting.Data["Student"][offset].Format())
                offset += 1
            input(f"Pro pokračování stiskni klávasu... (Již zobrazeno {offset} výsledků z {length})")
            cls()
def Konec():
    API.Logout()

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
    string = BakalariAPI.Looting.ToJSON()

    BakalariAPI.Looting.Data = {}
    BakalariAPI.Looting.IDs = {}

    BakalariAPI.Looting.FromJSON(string)
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


Login()
if shell:
    Shell()

Komens()
Znamky()
Schuzky()
Studenti()
Konec()