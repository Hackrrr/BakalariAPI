import argparse
import os
import requests
import BakalariAPI

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
args = parser.parse_args()

url = args.url
user = args.jmeno
password = args.heslo
interactive = args.interactive

def cls():
    os.system('cls' if os.name=='nt' else 'clear')

def AnoNeDialog() -> bool:
    while True:
        inputLetter = input("Zpráva vyžaduje potvrzení. Chcete potvrdit přečtení? Ano/Ne (y/n): ")[0].lower() # ano/yes/1 / ne/no/0
        if inputLetter in "ay1":
            return True
        elif inputLetter in "n0":
            return False
        print("Špatná hodnota")

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

print("Získávám zprávy...")
zpravyIDs = API.GetKomensIDs()
zpravy = []
for ID in zpravyIDs:
    print(f"Získávám Komens zprávu (ID: {ID})")
    zpravy.append(API.GetKomens(ID))
print("Zprávy získány, zobrazuji...")
if interactive:
    cls()
for zprava in zpravy:
    print("*** Zpráva ***")
    print(zprava.Format())
    print("\r\n\r\n")
    if interactive:
        if zprava.confirm and not zprava.confirmed and AnoNeDialog():
            print("Potvrzuji zprávu")
            zprava.Confirm()
        input("Pro pokračování stiskni klávasu...")
        cls()

print("Získávám známky...")
znamky = API.GetMarks()
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

API.Logout()