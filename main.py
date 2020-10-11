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

print(f"Kontrola stavu serveru/webu... ({url})")
loginURL = url
try:
    if BakalariAPI.JeServerOnline(url):
        print("Sever/web běží")
except BakalariAPI.Exceptions.ChybaVstupu:
    print("Neplatné URL schéma; Končím")
    exit(1)
except BakalariAPI.Exceptions.ChybaPripojeni:
    print("Severver/web (pravděpodobně) neběží; Končím")
    exit(1)

print(f"Pokus o přihlášení jako '{user}'")

try:
    session = BakalariAPI.Login(url, user, password)    
except BakalariAPI.Exceptions.ChybaAutentizace:
    print("Nepovedlo se přihlásit (nesprávné přihlašovací údaje)")
    exit(1)

print("Přihlášení úspěšné")

# Login done, now parse and extract

print("Získávám zprávy...")
#zpravyIDs = BakalariAPI.ZiskejKomensIDs(url, session)
zpravyIDs = BakalariAPI.ZiskejKomensIDs(url, session)
zpravy = []
for ID in zpravyIDs:
    print(f"Získávám Komens zprávu (ID: {ID})")
    zpravy.append(BakalariAPI.ZiskejKomens(url, session, ID))
print("Zprávy získány, zobrazuji...")
if interactive:
    cls()
for zprava in zpravy:
    print(zprava.Format())
    print("\r\n\r\n")
    if interactive:
        input("Pro pokračování stiskni klávasu...")
        cls()

print("Získávám známky...")
znamky = BakalariAPI.ZiskejZnamky(url, session)
print("Známky získány, zobrazuji...")
if interactive:
    cls()
for znamka in znamky:
    print(znamka.Format())
    print("\n")
    if interactive:
        input("Pro pokračování stiskni klávasu...")
        cls()

BakalariAPI.ProdluzPrihlaseni(url, session)