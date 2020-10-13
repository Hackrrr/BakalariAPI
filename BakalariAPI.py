"""Rádoby 'API' pro Bakaláře (resp. spíše scraper než API)"""
from __future__ import annotations
import warnings
from datetime import datetime, timedelta
import json
import re
import requests                         # Install
from bs4 import BeautifulSoup           # Install

import Exceptions



Endpoints = {
    "login":            "/login",
    "logout":           "/logout",
    "dashboard":        "/dashboard",
    "komens":           "/next/komens.aspx",
    "komens_get":    "/next/komens.aspx/GetMessageData",
    "komens_confirm":  "/next/komens.aspx/SetMessageConfirmed",
    "file":           "/next/getFile.aspx",
    "grades":           "/next/prubzna.aspx",
    "session_info":     "/sessioninfo",
    "session_extend":   "/sessionextend",
}



def IsHTTPScheme(url: str) -> bool:
    # Source: https://stackoverflow.com/questions/7160737/how-to-validate-a-url-in-python-malformed-or-not
    # TODO: Napsat si vlastní
    regex = re.compile(
        r'^(?:http)s?://' # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|' #domain...
        r'localhost|' #localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
        r'(?::\d+)?' # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return re.match(regex, url) != None



class Server:
    """Třída/objekt držící informace o serveru na kterém běží Bakaláři"""
    def __init__(self, url: str):
        if (not IsHTTPScheme(url)):
            raise Exceptions.InputException
        self.url: str = url
    
    def Running(self) -> bool:
        try:
            response = requests.get(self.url)
            response.raise_for_status()
            # if not response.url.endswith(Endpoints["login"]):
            #     warnings.warn(f"Server nepřesměroval na přihlašovací stránku (současná stránka: '{response.url}')", Exceptions.NecekaneChovani)
        #except requests.exceptions.RequestException as e:
        except requests.exceptions.RequestException:
            return False
        return True
    
    def GetEndpoint(self, endpoint: str) -> str:
        return self.url + Endpoints[endpoint]

class KomensFile:
    """Třída/objekt držící informace o Komens souboru/příloze na Bakalařích"""
    def __init__(self, ID: str, name: str, size: int, type: str, komensID: str, path: str, instance: BakalariAPI = None):
        self.ID: str = ID
        self.name: str = name
        self.size: int = size
        self.type: str = type
        self.komensID: str = komensID
        self.path: str = path
        self.instance: BakalariAPI = instance
    def GenerateURL(self):
        """Generuje (Sestaví) URL k souboru na serveru (SeverURL + Endpoint + ID_SOUBORU)"""
        return self.instance.server.GetEndpoint("file") + "?f=" + self.ID
    def DownloadStream(self) -> requests.Response:
        """Otevře stream na pro daný soubor pomocí 'requests' modulu a vrátí requests.Response, kterým lze iterovat pomocí metody '.iter_lines()'"""
        self.instance.session.get(self.GenerateURL(), stream=True)
    def Download(self, URL: str, session: requests.Session) -> bytes:
        """Stáhne daný soubor a vrátí ho jakožto (typ) byty (Doporučuje se ale použít metoda '.DownloadStream()', jelikož se zde soubor ukládá do paměti a ne na disk)"""
        return self.instance.session.get(self.GenerateURL()).content

class Komens:
    """Třída/objekt držící informace o Komens (zprávě/zprách)"""
    # Od, Zpráva, kdy, potvrdit, byla potvrzena?, "typ"
    def __init__(self, ID: str, sender: str, content: str, time: str, confirm: bool, confirmed: bool, type: str, readed: bool, files: list[KomensFile] = None, instance: BakalariAPI = None):
        self.ID: str = ID
        self.sender: str = sender
        self.rawContent: str = content
        self.time: datetime = datetime.strptime(time, "%d.%m.%Y %H:%M")
        self.confirm: bool = confirm
        self.confirmed: bool = confirmed
        self.type: str = type
        self.readed: bool = readed
        self.files: list[KomensFile] = files
        self.instance: BakalariAPI = instance
    @property
    def content(self) -> str:
        return BeautifulSoup(self.rawContent, "html.parser").prettify()
    def Confirm(self): #TODO: Some how refractor this...
        response = self.instance.session.post(self.instance.server.GetEndpoint("komens_confirm"), json={
            "idmsg": self.ID
        }).json()
        if not response["d"]:
            warnings.warn(f"Při potvrzování zprávy nebylo vráceno 'true', ale '{response['d']}'; Pravděpodobně nastala chyba; Celý objekt: {response}", Exceptions.UnexpectedBehaviour)
    def Format(self) -> str:
        return (
            f"ID: {self.ID}\n"
            f"Od: {self.sender}\n"
            f"Datum: {self.time.strftime('%d. %m. %Y, %H:%M')}\n"
            f"Vyžaduje potvrzení? {'Ano' if self.confirm else 'Ne'}; Potvrzena? {'Ano' if self.confirmed else 'Ne'}\n"
            f"Má soubory? {'Ano' if len(self.files) > 0 else 'Ne'}\n"
            "\n"
            f"{self.content}"
        )

class Grade:
    """Třída/objekt držící informace o Známkách/Klasifikaci"""
    def __init__(self, ID: str, subject: str, grade: str, weight: int, name: str, note1: str, note2: str, date1: str, date2: str, orderInClass: str, type: str, new: bool):
        self.ID: str = ID
        self.subject: str = subject
        self.grade: str = grade
        self.weight: int = weight
        self.name: str = name
        self.note1: str = note1
        self.note2: str = note2
        self.date1: datetime = datetime.strptime(date1, "%d.%m.%Y")
        self.date2: datetime = datetime.strptime(date2, "%d.%m.%Y")
        self.order: str = orderInClass
        self.type: str = type
        self.new: bool = new
    def Format(self):
        return (
            f"ID: {self.ID}\n"
            f"Předmět: {self.subject}\n"
            f"Název: {self.name}\n"
            f"Hodnota: {self.grade}\n"
            f"Váha: {self.weight}\n"
            f"Datum: {self.date1.strftime('%d. %m. %Y')}\n"
            f"Poznámka 1: {self.note1.strip()}\n" #TODO:Remove trailing new line
            f"Poznámka 2: {self.note2.strip()}" #TODO:Remove trailing new line
        )





"""
Pokud najdu JSON i učitelů, tak mergnu do class Osoba ze které budou derivovat studen a učitel/personál
"""
class Student:
    """Třída/objekt držící informace o studentovy"""
    def __init__(self, ID: str, jmeno: str, primeni: str, trida: str):
        self.ID: str = ID
        self.jmeno: str = jmeno
        self.primeni: str = primeni
        self.trida: str = trida


class BakalariAPI:
    """Třída/objekt který obsluhuje ostatní komponenty"""
    def __init__(self, server: Server, user: str, password: str, login: bool = True):
        self.server: Server = server
        self.user: str = user
        self.password: str = password
        self.session: requests.Session = requests.Session()
        if login:
            self.Login()

    def Login(self, init: bool = True):
        #TODO: Retry login X times
        try:
            self.session = requests.Session()
            response = self.session.post(self.server.GetEndpoint("login"), {
                "username": self.user,
                "password": self.password
            })
        except requests.exceptions.RequestException as e:
            raise Exceptions.ConnectionException from e
        if response.url == self.server.GetEndpoint("login"):
            raise Exceptions.AuthenticationException
        if not response.url.endswith(self.server.GetEndpoint("dashboard")):
            warnings.warn(f"Unexpected redirect on '{response.url}'", Exceptions.UnexpectedBehaviour)
        if init:
            pass
    def Logout(self):
        try:
            self.session.get(self.server.GetEndpoint("login") + "?s=-1")
        except requests.exceptions.RequestException as e:
            raise Exceptions.ConnectionException from e
        else:
            self.session = requests.Session()
    def Extend(self):
        try:
            self.session.get(self.server.GetEndpoint("session_extend"))
        except requests.exceptions.RequestException as e:
            raise Exceptions.ConnectionException from e


    def GetMarks(self, fromData: datetime = None) -> list[Grade]:
        output = []
        response = self.session.get(self.server.GetEndpoint("grades") + ("" if fromData == None else f"?dfrom={fromData.strftime('%Y%m%d')}0000&subt=obdobi"))
        soup = BeautifulSoup(response.content, "html.parser")
        znamkyList = soup.find(id="cphmain_DivBySubject")("div", attrs={"data-clasif": True})
        for znamka in znamkyList:
            data = json.loads(znamka["data-clasif"])
            output.append(Grade(
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
    def GetAllMarks(self) -> list[Grade]:
        return self.GetMarks(datetime(1, 1, 1))

    def GetKomensIDs(self, fromDate: datetime = None, toDate: datetime = None) -> list[str]:
        output = []
        target = self.server.GetEndpoint("komens")
        if fromDate != None or toDate != None:
            target += "?s=custom"
            if fromDate != None:
                target += "&from=" + fromDate.strftime("%d%m%Y")
            if toDate != None:
                target += "&to=" + toDate.strftime("%d%m%Y")
        response = self.session.get(target)
        soup = BeautifulSoup(response.content, "html.parser")
        komensList = soup.find(id="message_list_content").find("ul").find_all("li", recursive=False)
        for komens in komensList:
            output.append(komens.find("table")["data-idmsg"])
        return output
    def GetAllKomensIDs(self):
        return self.GetKomensIDs(datetime(1953, 1, 1), datetime.today() + timedelta(1))

    def GetKomens(self, ID: str, context: str = "prijate") -> Komens:
        response = self.session.post(self.server.GetEndpoint("komens_get"), json={
            "idmsg": ID,
            "context": context
        }).json()
        soubory = []
        if len(response["Files"]) != 0:
            for soubor in response["Files"]:
                soubory.append(KomensFile(
                    soubor["id"],
                    soubor["name"],
                    soubor["Size"],
                    soubor["type"],
                    soubor["idmsg"],
                    soubor["path"],
                    self
                ))
                if soubor["idmsg"] != ID:
                    warnings.warn(f"ID zprávy se neschoduje s ID zprávy referencované v souboru; ID zprávy: {ID}, ID v souboru: {soubor['idmsg']}", Exceptions.UnexpectedBehaviour)
        return Komens(
            ID,
            response["Jmeno"],
            response["MessageText"],
            response["Cas"],
            response["MohuPotvrdit"],
            response["Potvrzeno"],
            response["Kind"],
            response["CetlJsem"],
            soubory,
            self
        )