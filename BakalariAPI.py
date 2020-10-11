"""Rádoby 'API' pro Bakaláře (resp. spíše scraper než API)"""

import warnings
from datetime import datetime, timedelta
import json
import requests                         # Install
from bs4 import BeautifulSoup           # Install

import Exceptions

#TODO: Extract data-pageinfo from <head>

# Endpoints
Endpoint_Login = "/login"
Endpoint_Dashboard = "/dashboard"
Endpoint_Komens = "/next/komens.aspx"
"""
GET /next/komens.aspx?s=custom&from=DATUM_OD&to=DATUM_DO
Datum ve formátu DDMMYYYY; Nejmenší možný datum je 1. 1. 1753 (01011753). Nemám tušení proč zrovna tohle... Když už tak bych si tipl 1970, ale to funguje.
(Ok, mám odpověď - Protože (pravděpodobně) běží na starém SQL serveru (nebo používají starý věci, který používat nemají) - Starý SQL servery nepodporovaly datum
dřívější jak 1. 1. 1753 kvůli "chybějícím" dnům; Ref: https://stackoverflow.com/questions/3310569/what-is-the-significance-of-1-1-1753-in-sql-server)

<div ... id="message_list_content" ...>
    <ul>
        <li>
            <table ... data-idmsg="ID_ZPRAVY" ...> ... </table>
        </li>
        <li>
            <table ... data-idmsg="ID_ZPRAVY" ...> ... </table>
        </li>
        <li>
            <table ... data-idmsg="ID_ZPRAVY" ...> ... </table>
        </li>
        ...
    </ul>
</div>

ID zprávy začíná velkým u "U"

Takto dostaneme pouze přijaté zprávy. Pokud chceme odeslané, tak musíme přidta "l=o" do GET requestu ("celý název" je "l=odeslane", ale funguje to i zkráceně)
Bohužel nemůžu zatím otestovat, takže nevím, jestli funguje stejný postup na parsing
"""
Endpoint_Komens_Single = "/next/komens.aspx/GetMessageData"
"""
POST /next/komens.aspx/GetMessageData
{'idmsg':'ID_ZPRAVY', 'context':'prijate'}
"""
Endpoint_Komens_Potvrdit = "/next/komens.aspx/SetMessageConfirmed"
"""
POST /next/komens.aspx/SetMessageConfirmed
{'idmsg':'ID_ZPRAVY'}
    ↓ ↓ ↓
{"d": true}             Alespoň při úspěchu (a při chybě nejspíš false, ale nevím eShrug )
"""
Endpoint_Komens_Soubor = "/next/getFile.aspx"
"""
/next/getFile.aspx?f=ID_SOUBORU         (Pro budoucí badatele... Samozřejmě, že musíte mít validní session :) )
"""
#Endpoint_Komens_Odeslane = "/next/komens.aspx?l=o"
Endpoint_Ukoly = "/next/ukoly.aspx" # Pouze "Aktivní" (a pouze 20)
Endpoint_Znamky = "/next/prubzna.aspx"
"""
(<main><div id="predmety">)<div id="cphmain_DivBySubject">
    <div id="XX" class="predmet-radek">
        <div class="leva"> ... </div>
        <div class="znamky">
            <div id="ID_ZNAMKY" data-clasif="HTML_ENCODED_JSON_DATA"> ... </div>
            <div id="ID_ZNAMKY" data-clasif="HTML_ENCODED_JSON_DATA"> ... </div>
            <div id="ID_ZNAMKY" data-clasif="HTML_ENCODED_JSON_DATA"> ... </div>
            ...
        </div>
    </div>
    <div class='vyjed vyjed_XX'> ... </div>
    <div id="YY" class="predmet-radek"> ... </div>
    <div class='vyjed vyjed_YY'> ... </div>
    <div id="ZZ" class="predmet-radek"> ... </div>
    <div class='vyjed vyjed_ZZ'> ... </div>
    ...
</div>(</div></main>)

To XX, YY, ZZ je pravděpodobně ID předmětu, ale zatím jsem nenašel neviděl souvislosti :)
ID známky obsahuje i speciální znaky
"""
Endpoint_Suplovani = "/next/suplovani.aspx"
Endpoint_Rozvrh = "/next/rozvrh.aspx"
Endpoint_Akce = "/next/planakci.aspx"
Endpoint_Ankety = "/next/ankety.aspx"
Endpoint_Lifetime_Remaining = "/sessioninfo" #Vrátí zbýcající čas přihlášení; posílá se současná UNIX timestamp jako "_" GET parametr, ale funguje i bez toho
Endpoint_Lifetime_Extend = "/sessionextend" #Prodlouží čas přihlášení na 900s (= 15 minut); posílá se současná UNIX timestamp jako "_" GET parametr, ale funguje i bez toho
Endpoint_Nastenky = "/nastenky.aspx"
Endpoint_Schuzky = "/Collaboration/OnlineMeeting/MeetingsOverview"

class KomensSoubor:
    """Třída/objekt držící informace o Komens souboru/příloze na Bakalařích"""
    def __init__(self, ID: str, nazev: str, velikost: int, typ: str, ID_zpravy: str, cesta: str):
        self.ID: str = ID
        self.nazev: str = nazev
        self.velikost: int = velikost
        self.typ: str = typ
        self.ID_zpravy: str = ID_zpravy
        self.cesta: str = cesta #Absolutně nemám tušení, k čemu to je...
    def GenerujURL(self, URL: str):
        """Generuje (Sestaví) URL k souboru na serveru (SeverURL + Endpoint + ID_SOUBORU)"""
        return URL + Endpoint_Komens_Soubor + "?f=" + self.ID
    def Stream(self, URL: str, session: requests.Session) -> requests.Response:
        """Otevře stream na pro daný soubor pomocí 'requests' modulu a vrátí requests.Response, kterým lze iterovat pomocí metody '.iter_lines()'"""
        session.get(self.GenerujURL(URL), stream=True)
    def Stahni(self, URL: str, session: requests.Session) -> bytes:
        """Stáhne daný soubor a vrátí ho jakožto (typ) byty (Doporučuje se ale použít metoda '.Stream()', jelikož se zde soubor ukládá do paměti a ne na disk)"""
        return session.get(self.GenerujURL(URL)).content

class Komens:
    """Třída/objekt držící informace o Komens (zprávě/zprách)"""
    # Od, Zpráva, kdy, potvrdit, byla potvrzena?, "typ"
    def __init__(self, ID: str, odesilatel: str, obsah: str, cas: str, potvrdit: bool, potvrzeno: bool, typ: str, precteno: str, soubory: list[KomensSoubor] = None):
        self.ID: str = ID
        self.odesilatel: str = odesilatel
        self.rawObsah: str = obsah
        self.cas: datetime = datetime.strptime(cas, "%d.%m.%Y %H:%M")
        self.potvrdit: bool = potvrdit
        self.potvezeno: bool = potvrzeno
        self.typ: str = typ
        self.precteno: str = precteno
        self.soubory = soubory
    @property
    def obsah(self) -> str:
        return BeautifulSoup(self.rawObsah, "html.parser").prettify()
    def Potvrdit(self, URL: str, session: requests.session):
        response = session.post(URL + Endpoint_Komens_Potvrdit, json={
            "idmsg": self.ID
        }).json()
        if not response["d"]:
            warnings.warn(f"Při potvrzování zprávy nebylo vráceno 'true', ale '{response['d']}'; Pravděpodobně nastala chyba; Celý objekt: {response}", Exceptions.NecekaneChovani)
    def Format(self) -> str:
        return f"""***** Zpráva od {self.odesilatel}, přijata {self.cas.strftime("%d. %m. %Y, %H:%M")}; Typ: {self.typ}; ID: {self.ID} *****
Přečtena: {"Ano" if self.precteno else "Ne"}; Vyžaduje potvrzení: {f"Ano" if self.potvrdit else "Ne"}; Potvrzena: {"Ano" if self.potvezeno else "Ne"}
{self.obsah}
"""

class Ukol:
    """Třída/objekt držící informace o Úkolech"""
    pass

class Znamka:
    """Třída/objekt držící informace o Známkách/Klasifikaci"""
    def __init__(self, ID: str, predmet: str, znamka: str, vaha: int, nazev: str, poznamka1: str, poznamka2: str, datum1: str, datum2: str, poradiVeTride: str, typ: str, nova: bool):
        self.ID: str = ID
        self.predmet: str = predmet
        self.znamka: str = znamka
        self.vaha: int = vaha
        self.nazev: str = nazev
        self.poznamka1: str = poznamka1
        self.poznamka2: str = poznamka2
        self.datum1: datetime = datetime.strptime(datum1, "%d.%m.%Y")
        self.datum2: datetime = datetime.strptime(datum2, "%d.%m.%Y")
        self.poradi: str = poradiVeTride
        self.typ: str = typ
        self.nova: bool = nova
    def __str__(self):
        return self.znamka
    def Format(self):
        return f""" ***** Známka z předmětu {self.predmet}, "{self.nazev}" z {self.datum1.strftime("%d. %m. %Y")}; ID: {self.ID} *****
Hodnota: {self.znamka}; Váha: {self.vaha}
{self.poznamka1}
{self.poznamka2}
"""



def JeServerOnline(URL: str) -> bool:
    try:
        response = requests.get(URL)
        response.raise_for_status()
        if not response.url.endswith(Endpoint_Login):
            warnings.warn(f"Server nepřesměroval na přihlašovací stránku (současná stránka: '{response.url}')", Exceptions.NecekaneChovani)
    except (requests.exceptions.InvalidSchema, requests.exceptions.InvalidURL) as e:
        raise Exceptions.ChybaVstupu from e
    except requests.exceptions.BaseHTTPError as e:
        raise Exceptions.ChybaPripojeni from e
    except requests.exceptions.RequestException as e:
        raise Exceptions.ChybaPripojeni from e
    return True

#TODO: Retry login X times
def Login(URL: str, user: str, password: str) -> requests.Session:
    session = requests.session()
    response = session.post(URL + Endpoint_Login, {
        "username": user,
        "password": password
    })
    if response.url.endswith(Endpoint_Login):
        raise Exceptions.ChybaAutentizace
    if not response.url.endswith(Endpoint_Dashboard):
        warnings.warn(f"Neočekavané přesměrování na '{response.url}'", Exceptions.NecekaneChovani)
    return session

def ProdluzPrihlaseni(URL: str, session: requests.Session):
    session.get(URL + Endpoint_Lifetime_Extend)

def ZiskejKomens(URL: str, session: requests.Session, ID: str, kontext: str = "prijate") -> Komens:
    response = session.post(URL + Endpoint_Komens_Single, json={
        "idmsg": ID,
        "context": kontext
    }).json()
    soubory = None
    if len(response["Files"]) != 0:
        soubory = []
        for soubor in response["Files"]:
            soubory.append(KomensSoubor(
                soubor["id"],
                soubor["name"],
                soubor["Size"],
                soubor["type"],
                soubor["idmsg"],
                soubor["path"]
            ))
            if soubor["idmsg"] != ID:
                warnings.warn(f"ID zprávy se neschoduje s ID zprávy referencované v souboru; ID zprávy: {ID}, ID v souboru: {soubor['idmsg']}", Exceptions.NecekaneChovani)
    return Komens(
        ID,
        response["Jmeno"],
        response["MessageText"],
        response["Cas"],
        response["MohuPotvrdit"],
        response["Potvrzeno"],
        response["Kind"],
        response["CetlJsem"],
        soubory
    )

def ZiskejKomensIDs(URL: str, session: requests.Session, od: datetime = None, do: datetime = None) -> list[str]:
    output = []
    target = URL + Endpoint_Komens
    if od != None or do != None:
        target += "?s=custom"
        if od != None:
            target += "&from=" + od.strftime("%d%m%Y")
        if do != None:
            target += "&to=" + do.strftime("%d%m%Y")
    response = session.get(target)
    soup = BeautifulSoup(response.content, "html.parser")
    komensList = soup.find(id="message_list_content").find("ul").find_all("li", recursive=False)
    for komens in komensList:
        output.append(komens.find("table")["data-idmsg"])
    return output

def ZiskejVsechnyKomensIDs(URL: str, session: requests.Session):
    return ZiskejKomensIDs(URL, session, datetime(1953, 1, 1), datetime.today() + timedelta(1))

def ZiskejZnamky(URL: str, session: requests.Session) -> list[Znamka]:
    output = []
    response = session.get(URL + Endpoint_Znamky+ "?dfrom=0001010000&subt=obdobi")
    soup = BeautifulSoup(response.content, "html.parser")
    znamkyList = soup.find(id="cphmain_DivBySubject")("div", attrs={"data-clasif": True})
    for znamka in znamkyList:
        data = json.loads(znamka["data-clasif"])
        output.append(Znamka(
            data["id"],
            data["nazev"],
            data["MarkText"],
            data["vaha"],
            data["caption"],
            data["poznamkakzobrazeni"],
            data["MarkTooltip"] if data["MarkTooltip"] != None else "",
            data["strdatum"],
            data["udel_datum"],
            data["strporadivetrideuplne"],
            data["typ"],
            data["IsNew"]
        ))
    return output
            
# def ZiskejUkoly(URL: str, session: requests.Session) -> list[Ukol]:
#     output = []
#     response = session.post(URL + Endpoint_Ukoly, json={
#         "": "200", #Počet úkolů (pravděpodobně); Najít tohle byl extrémní pain, takže doufám, že je to ono... (Chrome totiž robrazí POST data které jsou "&=HODNOTA" jakožto "(empty)", takže se nejde "normálně" podívat, co to je)
#         "cphmain_drpDate_VI": "all"
#     })
#     soup = BeautifulSoup(response.content, "html.parser")
#     element = soup.find(id="cphmain_drpDate_I")
#     print(element.prettify())
#     return
#     ukolyList = soup.find(id="grdukoly_DXMainTable")("tr", attrs={"data-clasif": True})









Endpoints = {
    "login":            "/login",
    "dashboard":        "/dashboard",
    "komens":           "/next/komens.aspx",
    "komens_ziskej":    "/next/komens.aspx/GetMessageData",
    "komens_potvrdit":  "/next/komens.aspx/SetMessageConfirmed",
    "soubor":           "/next/getFile.aspx",
    "znamky":           "/next/prubzna.aspx"
}

#Endpoint_Komens_Odeslane = "/next/komens.aspx?l=o"
Endpoint_Ukoly = "/next/ukoly.aspx" # Pouze "Aktivní" (a pouze 20)
Endpoint_Rozvrh = "/next/rozvrh.aspx"
Endpoint_Lifetime_Remaining = "/sessioninfo" #Vrátí zbýcající čas přihlášení; posílá se současná UNIX timestamp jako "_" GET parametr, ale funguje i bez toho
Endpoint_Lifetime_Extend = "/sessionextend" #Prodlouží čas přihlášení na 900s (= 15 minut); posílá se současná UNIX timestamp jako "_" GET parametr, ale funguje i bez toho


class Server:
    """Třída/objekt držící informace o serveru na kterém běží Bakaláři"""
    def __init__(self, url: str):
        self.url = url
    
    def Bezi(self) -> bool:
        try:
            response = requests.get(self.url)
            response.raise_for_status()
            if not response.url.endswith(Endpoint_Login):
                warnings.warn(f"Server nepřesměroval na přihlašovací stránku (současná stránka: '{response.url}')", Exceptions.NecekaneChovani)
        except (requests.exceptions.InvalidSchema, requests.exceptions.InvalidURL) as e:
            raise Exceptions.ChybaVstupu from e
        except requests.exceptions.BaseHTTPError as e:
            raise Exceptions.ChybaPripojeni from e
        except requests.exceptions.RequestException as e:
            raise Exceptions.ChybaPripojeni from e
        return True
    
    def ZiskejEndpoint(self, endpoint: str) -> str:
        pass

class Uzivatel:
    def __init__(self, jmeno: str, heslo: str):
        self.jmeno = jmeno
        self.heslo = heslo
        

class Session:
    def __init__(self, server: Server, uzivatel: Uzivatel, login: bool):
        self.server = server
        self.uzivatel = uzivatel
        self.session: requests.Session = requests.Session()


    def Login(self):
        session = requests.session()
        response = session.post(self.server.url + Endpoint_Login, {
            "username": user,
            "password": password
        })
        if response.url.endswith(Endpoint_Login):
            raise Exceptions.ChybaAutentizace
        if not response.url.endswith(Endpoint_Dashboard):
            warnings.warn(f"Neočekavané přesměrování na '{response.url}'", Exceptions.NecekaneChovani)
        return session