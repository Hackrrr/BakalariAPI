import argparse
import os
import requests
import BakalariAPI
from datetime import datetime, timedelta, timezone # Here it comes... Timezone hadndling first feel PepeLaugh
# Hej! Moje budoucí já... Já vím, že se sem jednou podíváš... Takže až ta chvíle nastane, tak si vzpomeň, že za 100 let budou tenhle samej problém
# s časovými pásmy řešit furt :) Takže nevadí, že si to pořád ještě po 10h debugu nespravil...
# HA! Dělám si srandu. Padej to opravit! S láskou - Tvoje minulé já :)
import webbrowser

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
    "-t", "--test",
    default=False,
    action="store_true",
    help="Test snippet"
)
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
test = args.test

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
def Timedelta2Tuple(delta: timedelta) -> tuple[int, int, int, int]: # days, hours, minutes, seconds
    seconds = delta.seconds % 60 # TODO: Test
    minutes = (delta.seconds - seconds) % 60
    hours = (delta.seconds - (minutes * 60 + seconds)) % 24
    days = delta.days
    return (days, hours, minutes, seconds)


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

if not API.server.Running():
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
#TODO: Init
# Login done, now parse and extract



if test:
    
    exit(0)





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
    # except KeyboardInterrupt:
    #     print("Debug mód aktivní... Příkazy:")
    #     DebugMode()

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

schuzkyIDs = API.GetMettingsIDs()
print("IDčka online schůzek získany")
schuzky = []
for ID in schuzkyIDs:
    print(f"Získávám online chůzku {ID}")
    schuzky.append(API.GetMeeting(ID))
print("Zprávy získány, zobrazuji...")
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

if interactive and AnoNeDialog("Při získávání schůzek se podařilo získat seznam všech studentů. Chcete jej zobrazit? "):
    count = InputCislo("Kolik výsledků najednou? (Výchozí 25) ", 25)
    offset = 0
    length = len(API.Students)
    cls()
    while offset < length:
        for x in range(count):
            if (offset >= length):
                break
            print(API.Students[offset].Format())
            offset += 1
        input(f"Pro pokračování stiskni klávasu... (Již zobrazeno {offset} výsledků z {length})")
        cls()







API.Logout()