"""Rádoby 'API' pro Bakaláře (resp. spíše scraper než API)"""
from __future__ import annotations

import inspect
import json
import re
import sys
import warnings
from abc import ABC, abstractmethod
from enum import Enum                   # Není nutno instalovat pro Python 3.4+, předcházející verze: pip install enum34
from datetime import datetime, timedelta

import requests                         # Install
from bs4 import BeautifulSoup           # Install
try:
    from selenium import webdriver      # Install + Download some WebDriver
except ImportError:
    print("Import Selenium se nezdařil a pravděpodobně není nainstalován, některé funkce budou nedostupné")

class Exception(Exception):
    """Základní exception classa pro BakalariAPI
    Všechny výjimky mají dědičnou cestu k této výjimky"""
class AuthenticationException(Exception):
    """Výjimka při autentizaci"""
class ConnectionException(Exception):
    """Výjimka při chybě při pokusu o připojení - Server nebo Bakaláři pravděpodobně neběží"""
class InputException(Exception):
    """Výjimka při chybném vstupu"""
class UserNotLoggedIn(Exception):
    """Výjimka při pokusu o vykonání autentizované akci, když uživatel není přihlášen"""

class Warning(UserWarning):
     """Základní warning classa pro BakalariAPI
    Všechny varování mají dědičnou cestu k tomuto varování"""
class UnexpectedBehaviour(Warning):
    """Nečekaná odpoveď/přesměrování od serveru (pravděpodobně na serveru běží jiná (nová) veze Bakalařů)"""
class DifferentVersion(Warning):
    """Bakaláři mají jinou verzi, než BakalariAPI podporuje"""
class SameID(Warning):
    """Nalezeny objekty (při zpracování/ukládání výsledků), které mají stejné ID ale nejsou totožný
    Pozn.: Mohou být i totžný, ale není to jedna a ta samá instance (prostě OOP)"""


LAST_SUPPORTED_VERSION = "1.36.1207.1"


Endpoints = {
    "login":                "/login",
    "logout":               "/logout",
    "dashboard":            "/dashboard",
    "komens":               "/next/komens.aspx",
    "komens_get":           "/next/komens.aspx/GetMessageData",
    "komens_confirm":       "/next/komens.aspx/SetMessageConfirmed",
    "file":                 "/next/getFile.aspx",
    "grades":               "/next/prubzna.aspx",
    "session_info":         "/sessioninfo",
    "session_extend":       "/sessionextend",
    #"meetings":             "/Collaboration/OnlineMeeting",
    "meetings_overview":    "/Collaboration/OnlineMeeting/MeetingsOverview",
    "meetings_info":        "/Collaboration/OnlineMeeting/Detail/",
    "user_info":            "/next/osobni_udaje.aspx",
    "homeworks":            "/next/ukoly.aspx",
    "homeworks_done":       "/HomeWorks/MarkAsFinished"
}


class Browser(Enum):
    """
    Enum prohlížečů/browserů podporovaných Seleniem
    """
    Chrome      = 0
    Firefox     = 1
    Edge        = 2
    Safari      = 3
    Opera       = 4
    IE          = 5
    Android     = 6
    BlackBerry  = 7
    PhantomJS   = 8
    WebKitGTK   = 9
    Remote      = 10
class SeleniumHandler:
    """
    Classa obsahujcí nastavení pro Selenium
    """
    def __init__(self, browser: Browser, executablePath: str = "", params: dict = {}):
        if "selenium" not in sys.modules:
            raise ImportError(name="selenium")
        self.Browser: Browser = browser
        self.ExecutablePath: str = executablePath
        self.Params: dict = params
    def open(self) -> webdriver:
        driver = None
        path = {"executable_path":self.ExecutablePath} if self.ExecutablePath != "" and self.ExecutablePath != None else {}
        if self.Browser == Browser.Chrome:
            driver = webdriver.Chrome(**path, **self.Params)
        elif self.Browser == Browser.Firefox:
            driver = webdriver.Firefox(**path, **self.Params)
        elif self.Browser == Browser.Edge:
            driver = webdriver.Edge(**path, **self.Params)
        elif self.Browser == Browser.Safari:
            driver = webdriver.Safari(**path, **self.Params)
        elif self.Browser == Browser.Opera:
            driver = webdriver.Opera(**path, **self.Params)
        elif self.Browser == Browser.IE:
            driver = webdriver.Ie(**path, **self.Params)
        elif self.Browser == Browser.Android:
            driver = webdriver.Android(**self.Params)
        elif self.Browser == Browser.BlackBerry:
            # Potřebné parametry (asi :) ): device_password: PASSWORD, hostip: "169.254.0.1"
            driver = webdriver.BlackBerry(**self.Params)
        elif self.Browser == Browser.PhantomJS:
            driver = webdriver.PhantomJS(**path, **self.Params)
        elif self.Browser == Browser.WebKitGTK:
            driver = webdriver.WebKitGTK(**path, **self.Params)
        elif self.Browser == Browser.Remote:
            # Potřebné parametry (asi :) ): command_executor: "http://127.0.0.1:4444/wd/hub"
            driver = webdriver.Remote(**self.Params)
        else:
            raise ValueError()
        return driver



def IsHTTPScheme(url: str) -> bool:
    # Source: https://stackoverflow.com/questions/7160737/how-to-validate-a-url-in-python-malformed-or-not
    regex = re.compile(
        r'^(?:http)s?://' # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|' #domain...
        r'localhost|' #localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
        r'(?::\d+)?' # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return re.match(regex, url) != None
def LineIterator(text: str):
    prevnl = -1
    while True:
      nextnl = text.find('\n', prevnl + 1)
      if nextnl < 0: break
      yield text[prevnl + 1:nextnl]
      prevnl = nextnl
def FindAll(text: str, sub: str, overlaping: bool = True) -> list[int]:
    """Vrátí všechny indexy, na kterých se nachází (sub)string"""
    output = []
    offset = 0
    while True:
        position = text.find(sub, offset)
        if position == -1:
            return output
        output.append(position)
        offset += 1 if overlaping else len(sub)
def GetText(soup: BeautifulSoup) -> str:
    """BeautifulSoup.get_text(), ale tak trochu jinak
    BeautifulSoup dělá vynikající práci... Ale na prasárny Bakalářů to ani tak nestačí
    To co tohle udělá a '.get_text()' ne:
        - Nahradí "<br/>" za \n... '.get_text()' zvládá jen syntakticky správně (tedy "<br />" nebo jen "<br>")
        - Pokud je zde "<body>" tag, tak vezme jen ten
        - Stripne text (Je to vůbec potřeba? eShrug)
    """
    #TODO: Text Wrapping?
    for br in soup("br"):
        br.replace_with("\n" + br.text)

    body = soup.find("body")
    if body != None:
        soup = body
    
    return soup.get_text().strip()
def First2Upper(string: str) -> str:
    return string[0].upper() + string[1:]
def String2Datetime(string: str) -> datetime:
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S%z",
        "%Y-%m-%d %H:%M:%ST%z",
        "%Y-%m-%d"
    ]
    for format in formats:
        try:
            return datetime.strptime(string, format)
        except ValueError:
            pass
    raise ValueError


class Server:
    """Třída/objekt držící informace o serveru na kterém běží Bakaláři"""
    def __init__(self, url: str):
        if (not IsHTTPScheme(url)):
            raise InputException
        self.Url: str = url
        self.Version: str = None
        self.VersionDate: datetime = None
        self.RegistrationNumber: int = None

    def Running(self) -> bool:
        try:
            response = requests.get(self.Url)
            response.raise_for_status()
        #except requests.exceptions.RequestException as e:
        except requests.exceptions.RequestException:
            return False
        return True
    
    def GetEndpoint(self, endpoint: str) -> str:
        return self.Url + Endpoints[endpoint]

class BakalariObject(ABC):
    def __init__(self, ID: str):
        self.ID = ID
    def __eq__(self, other: BakalariObject):
        return self.ID == other.ID
    @abstractmethod
    def Format(self) -> str:
        pass
    

class BakalariFile(BakalariObject):
    """Třída/objekt držící informace o souboru/příloze na Bakalařích"""
    def __init__(self, ID: str, name: str, size: int, type: str = ""):
        self.ID: str = ID
        self.Name: str = name
        self.Size: int = size
        self.Type: str = type

    def GenerateURL(self, server: Server):
        """Generuje (Sestaví) URL k souboru na serveru (SeverURL + Endpoint + ID_SOUBORU)"""
        if type(server) is BakalariAPI:
            server = server.Server
        return server.GetEndpoint("file") + "?f=" + self.ID

    def DownloadStream(self, instance: BakalariAPI) -> requests.Response:
        """Otevře stream na pro daný soubor pomocí 'requests' modulu a vrátí requests.Response, kterým lze iterovat pomocí metody '.iter_lines()'"""
        instance.Session.get(self.GenerateURL(instance.server), stream=True)

    def Download(self, instance: BakalariAPI) -> bytes:
        """Stáhne daný soubor a vrátí ho jakožto (typ) byty (Doporučuje se ale použít metoda '.DownloadStream()', jelikož se zde soubor ukládá do paměti a ne na disk)"""
        return instance.Session.get(self.GenerateURL(instance.server)).content

    def Format(self) -> str:
        return (
            f"ID: {self.ID}\n"
            f"Název souboru: {self.Name}\n"
            f"Typ: {self.Type}\n"
            f"Velikost: {self.Size}"
        )

class KomensFile(BakalariFile):
    """Třída/objekt držící informace o Komens souboru/příloze na Bakalařích"""
    def __init__(self, ID: str, name: str, size: int, type: str, komensID: str, path: str):
        super(KomensFile, self).__init__(ID, name, size, type)
        self.KomensID: str = komensID
        self.Path: str = path
    def Format(self) -> str:
        return (
            f"ID: {self.ID}\n"
            f"Název souboru: {self.Name}\n"
            f"Typ: {self.Type}\n"
            f"Velikost: {self.Size}\n"
            f"ID přidružené zprávy: {self.KomensID}\n"
            f"(Nepoužitelná) Cesta: {self.Path}\n"
        )

class Komens(BakalariObject):
    """Třída/objekt držící informace o Komens (zprávě/zprách)"""
    def __init__(self, ID: str, sender: str, content: str, time: datetime, confirm: bool, confirmed: bool, type: str, files: list[KomensFile] = None, instance: BakalariAPI = None):
        super(Komens, self).__init__(ID)
        self.Sender: str = sender
        self.Content: str = content
        self.Time: datetime = time
        self.NeedsConfirm: bool = confirm
        self.Confirmed: bool = confirmed
        self.Type: str = type
        self.Files: list[KomensFile] = files
        self.Instance: BakalariAPI = instance
    # @property
    # def Content(self) -> str:
    #     return BeautifulSoup(self.RawContent, "html.parser").prettify()
    def Confirm(self):
        response = self.Instance.Session.post(self.Instance.Server.GetEndpoint("komens_confirm"), json={
            "idmsg": self.ID
        }).json() # Jakože tohle jen jen ztráta výkonu... Actually to nemusíme vůbec parsovat...
        if not response["d"]:
            warnings.warn(f"Při potvrzování zprávy nebylo vráceno 'true', ale '{response['d']}'; Pravděpodobně nastala chyba; Celý objekt: {response}", UnexpectedBehaviour)
    def Format(self) -> str:
        return (
            f"ID: {self.ID}\n"
            f"Od: {self.Sender}\n"
            f"Datum: {self.Time.strftime('%d. %m. %Y, %H:%M')}\n"
            f"Vyžaduje potvrzení? {'Ano' if self.NeedsConfirm else 'Ne'}; Potvrzena? {'Ano' if self.Confirmed else 'Ne'}\n"
            f"Má soubory? {'Ano' if len(self.Files) > 0 else 'Ne'}\n"
            "\n"
            f"{GetText(BeautifulSoup(self.Content, 'html.parser'))}" #.get_text().strip()
        )

class Grade(BakalariObject):
    """Třída/objekt držící informace o Známkách/Klasifikaci"""
    def __init__(self, ID: str, subject: str, grade: str, weight: int, name: str, note1: str, note2: str, date1: datetime, date2: datetime, orderInClass: str, type: str):
        super(Grade, self).__init__(ID)
        self.Subject: str = subject
        self.Grade: str = grade
        self.Weight: int = weight
        self.Name: str = name
        self.Note1: str = note1
        self.Note2: str = note2
        self.Date1: datetime = date1
        self.Date2: datetime = date2
        self.OrderInClass: str = orderInClass
        self.Type: str = type
        #self.Target: str = target
    def Format(self):
        return (
            f"ID: {self.ID}\n"
            f"Předmět: {self.Subject}\n"
            f"Název: {self.Name}\n"
            f"Hodnota: {self.Grade}\n"
            f"Váha: {self.Weight}\n"
            f"Datum: {self.Date1.strftime('%d. %m. %Y')}\n"
            f"Poznámka 1: {self.Note1.strip()}\n"
            f"Poznámka 2: {self.Note2.strip()}"
        )

class Meeting(BakalariObject):
    """Třída/objekt držící informace o Známkách/Klasifikaci"""                                                                                                                          # ID + time
    def __init__(self, ID: str, ownerID: str, name: str, content: str, startTime: datetime, endTime: datetime, joinURL: str, participants: list[tuple[str, str]], participantsReadInfo: list[tuple[str, datetime]]):
        super(Meeting, self).__init__(ID)
        self.OwnerID: str = ownerID
        self.Name: str = name
        self.Content: str = content
        self.StartTime: datetime = startTime
        self.EndTime: datetime = endTime
        self.JoinURL: str = joinURL
        self.Participants: list[tuple[str, str]] = participants # ID, (Celé) Jméno
        self.ParticipantsReadInfo: list[tuple[str, datetime]] = participantsReadInfo # ID, Čas přečtení
    @property
    def OwnerName(self):
        for participant in self.Participants:
            if participant[0] == self.OwnerID:
                return participant[1]
    def Format(self) -> str:
        return (
            f"ID: {self.ID}\n"
            f"Pořadatel: {self.OwnerName}\n"
            f"Začátek: {self.StartTime.strftime('%H:%M, %d. %m. %Y')}\n"
            f"Konec:   {self.EndTime.strftime('%H:%M, %d. %m. %Y')}\n"
            f"URL na připojení: {self.JoinURL}\n"
            f"Název: {self.Name.strip()}\n"
            "\n"
            f"{GetText(BeautifulSoup(self.Content, 'html.parser'))}"
        )

class Student(BakalariObject):
    """Třída/objekt držící informace o studentovy"""
    def __init__(self, ID: str, name: str, surname: str, _class: str):
        super(Student, self).__init__(ID)
        self.Name: str = name
        self.Surname: str = surname
        self.Class: str = _class
    def Format(self) -> str:
        return f"{self.ID}: {self.Name} {self.Surname} ({self.Class})"

class Homework(BakalariObject):
    """Třída/objekt držící informace o domacím úkolu"""
    def __init__(self, ID: str, submissionDate: datetime, subject: str, content: str, assignmentDate: datetime, done: bool):
        super(Homework, self).__init__(ID)
        self.SubmissionDate: datetime = submissionDate
        self.Subject: str = subject
        self.Content: str = content
        self.AssignmentDate: datetime = assignmentDate
        self.Done: bool = done
    def Format(self) -> str:
        return (
            f"ID: {self.ID}\n"
            f"Datum odevzdaní: {self.SubmissionDate.strftime('%d. %m.')}\n"
            f"Datum zadání: {self.AssignmentDate.strftime('%d. %m.')}\n"
            f"Předmět: {self.Subject}\n"
            f"Hotovo? {'Ano' if self.Done else 'Ne'}\n"
            "\n"
            f"{GetText(BeautifulSoup(self.Content, 'html.parser'))}"
        )

class BakalariAPI:
    """Třída/objekt který obsluhuje ostatní komponenty"""
    def __init__(self, server: Server, user: str, password: str, login: bool = True, looting: bool = True, seleniumSettings: SeleniumHandler = None):
        self.Server: Server = server
        self.User: str = user
        self.Password: str = password
        self.Session: requests.Session = requests.Session()
        self.Looting: bool = looting
        self.Loot: Looting = Looting() if self.Looting else None
        self.Selenium: SeleniumHandler = seleniumSettings

        self.UserType: str = None
        self.UserHash: str = None
        if login:
            self.Login()

    def Init(self):
        try:
            soup = BeautifulSoup(self.Session.get(self.Server.GetEndpoint("user_info")).content, "html.parser")
        except requests.exceptions.RequestException as e:
            raise ConnectionException from e
        data = json.loads(soup.head["data-pageinfo"])
        self.UserType = data["userType"]
        self.UserHash = data["userHash"]
        self.Server.Version = data["applicationVersion"]
        # if data["applicationVersion"] != LAST_SUPPORTED_VERSION:
        #     warnings.warn("Server runs diffentt version than we support", Exceptions.DifferentVersion)
        self.Server.VersionDate = datetime.strptime(data["appVersion"], "%Y%m%d")
        self.Server.RegistrationNumber = int(data["evidNumber"])
    
    def Login(self, init: bool = True):
        try:
            self.Session = requests.Session()
            response = self.Session.post(self.Server.GetEndpoint("login"), {
                "username": self.User,
                "password": self.Password
            })
        except requests.exceptions.RequestException as e:
            raise ConnectionException from e
        if response.url == self.Server.GetEndpoint("login"):
            raise AuthenticationException
        if not response.url.endswith(self.Server.GetEndpoint("dashboard")):
            warnings.warn(f"Unexpected redirect on '{response.url}'", UnexpectedBehaviour)
        if init:
            self.Init()
    def Logout(self):
        try:
            self.Session.get(self.Server.GetEndpoint("login") + "?s=-1")
        except requests.exceptions.RequestException as e:
            raise ConnectionException from e
        else:
            self.Session = requests.Session()
    def Extend(self):
        try:
            self.Session.get(self.Server.GetEndpoint("session_extend"))
        except requests.exceptions.RequestException as e:
            raise ConnectionException from e

    def GetGrades(self, fromDate: datetime = None) -> list[Grade]:
        output = []
        try:
            response = self.Session.get(self.Server.GetEndpoint("grades") + ("" if fromDate == None else f"?dfrom={fromDate.strftime('%Y%m%d')}0000&subt=obdobi"))
        except requests.exceptions.RequestException as e:
            raise ConnectionException from e
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
                datetime.strptime(data["strdatum"], "%d.%m.%Y"),
                datetime.strptime(data["udel_datum"], "%d.%m.%Y"),
                data["strporadivetrideuplne"],
                data["typ"]
            ))
        if self.Looting:
            for item in output:
                self.Loot.AddLoot(item)
        return output
    def GetAllGrades(self) -> list[Grade]:
        return self.GetGrades(datetime(1, 1, 1))

    def GetKomensIDs(self, fromDate: datetime = None, toDate: datetime = None) -> list[str]:
        output = []
        target = self.Server.GetEndpoint("komens")
        if fromDate != None or toDate != None:
            target += "?s=custom"
            if fromDate != None:
                target += "&from=" + fromDate.strftime("%d%m%Y")
            if toDate != None:
                target += "&to=" + toDate.strftime("%d%m%Y")
        try:
            response = self.Session.get(target)
        except requests.exceptions.RequestException as e:
            raise ConnectionException from e
        soup = BeautifulSoup(response.content, "html.parser")
        komensList = soup.find(id="message_list_content").find("ul").find_all("li", recursive=False)
        for komens in komensList:
            output.append(komens.find("table")["data-idmsg"])
        return output
    def GetAllKomensIDs(self):
        return self.GetKomensIDs(datetime(1953, 1, 1), datetime.today() + timedelta(1))

    def GetKomens(self, ID: str, context: str = "prijate") -> Komens:
        try:
            response = self.Session.post(self.Server.GetEndpoint("komens_get"), json={
                "idmsg": ID,
                "context": context
            }).json()
        except requests.exceptions.RequestException as e:
            raise ConnectionException from e
        soubory = []
        if len(response["Files"]) != 0:
            for soubor in response["Files"]:
                komensFile = KomensFile(
                    soubor["id"],
                    soubor["name"],
                    soubor["Size"],
                    soubor["type"],
                    soubor["idmsg"],
                    soubor["path"],
                )
                soubory.append(komensFile)
                if soubor["idmsg"] != ID:
                    warnings.warn(f"ID zprávy se neschoduje s ID zprávy referencované v souboru; ID zprávy: {ID}, ID v souboru: {soubor['idmsg']}", UnexpectedBehaviour)
            if self.Looting:
                for item in soubory:
                    self.Loot.AddLoot(item)
        komens = Komens(
            ID,
            response["Jmeno"],
            response["MessageText"],
            datetime.strptime(response["Cas"], "%d.%m.%Y %H:%M"),
            response["MohuPotvrdit"],
            response["Potvrzeno"],
            response["Kind"],
            soubory,
            self
        )
        if self.Looting:
            self.Loot.AddLoot(komens)
        return komens

    def GetMeetingsIDs(self, lootStudents: bool = True) -> list[str]:
        output = []
        try:
            response = self.Session.get(self.Server.GetEndpoint("meetings_overview"))
        except requests.exceptions.RequestException as e:
            raise ConnectionException from e
        soup = BeautifulSoup(response.content, "html.parser")
        scritps = soup.head("script")
        for script in scritps:
            formated = script.prettify()
            if "var model = " in formated:
                break
        loot = {
            "Meetings": False,
            "Students": False
        }
        for line in LineIterator(formated):
            line = line.strip()
            if line.startswith("var meetingsData = "):
                loot["Meetings"] = True
                meetingsJSON = json.loads(line.strip()[len("var meetingsData = "):-1])
                for meeting in meetingsJSON:
                    output.append(str(meeting["Id"])) # Actually je to číslo, ale všechny ostaní IDčka jsou string, takže se budeme tvářit že je string i tohle...
            elif lootStudents and line.startswith("model.Students = ko.mapping.fromJS("):
                loot["Students"] = True
                studentsJSON = json.loads(line.strip()[len("model.Students = ko.mapping.fromJS("):-2])
                for student in studentsJSON:
                    self.Loot.AddLoot(Student(
                        student["Id"],
                        student["Name"],
                        student["Surname"],
                        student["Class"]
                    ))
            if loot["Meetings"] and (not lootStudents or loot["Students"]):
                break
        return output
    def GetMeetingsIDsNew(self, fromDate: datetime, toDate: datetime) -> list[str]:
        try:
            output = []
            response = self.Session.post(self.Server.GetEndpoint("meetings_overview"), {
                "TimeWindow": "FromTo",
                "FilterByAuthor": "AllInvitations",
                "MeetingFrom": fromDate.strftime("%Y-%m-%dT%H:%M:%S") + "+00:00",
                "MeetingTo": toDate.strftime("%Y-%m-%dT%H:%M:%S") + "+00:00"
            }).json()
            for meeting in response["data"]["Meetings"]:
                output.append(str(meeting["Id"]))
            return output
        except requests.exceptions.RequestException as e:
            raise ConnectionException from e
    def GetAllMeetingsIDs(self) -> list[str]:
        return self.GetMeetingsIDsNew(datetime(1, 1, 1), datetime(9999, 12, 31, 23, 59, 59))
    def GetMeeting(self, ID: str) -> Meeting:
        try:
            response = self.Session.get(self.Server.GetEndpoint("meetings_info") + ID).json()
        except requests.exceptions.RequestException as e:
            raise ConnectionException from e
        if not response["success"]:
            return None
        meeting = Meeting(
            response["data"]["Id"],
            response["data"]["OwnerId"],
            response["data"]["Title"],
            response["data"]["Details"],
            datetime.strptime(response["data"]["MeetingStart"], "%Y-%m-%dT%H:%M:%S%z"),
            datetime.strptime(response["data"]["MeetingEnd"], "%Y-%m-%dT%H:%M:%S%z"),
            response["data"]["JoinMeetingUrl"],
            [(s["PersonId"], s["PersonName"]) for s in response["data"]["Participants"]],
            [(s["PersonId"], datetime.strptime(s["Readed"][:-(len(s["Readed"]) - s["Readed"].rfind("."))], "%Y-%m-%dT%H:%M:%S")) for s in response["data"]["ParticipantsListOfRead"]]
        )
        if self.Looting:
            self.Loot.AddLoot(meeting)
        return meeting

    def GetStudents(self) -> list[Student]:
        output = []
        try:
            response = self.Session.get(self.Server.GetEndpoint("meetings_overview"))
        except requests.exceptions.RequestException as e:
            raise ConnectionException from e
        soup = BeautifulSoup(response.content, "html.parser")
        scritps = soup.head("script")
        for script in scritps:
            formated = script.prettify()
            if "var model = " in formated:
                break
        for line in LineIterator(formated):
            line = line.strip()
            if line.startswith("model.Students = ko.mapping.fromJS("):
                studentsJSON = json.loads(line.strip()[len("model.Students = ko.mapping.fromJS("):-2])
                for student in studentsJSON:
                    output.append(Student(
                        student["Id"],
                        student["Name"],
                        student["Surname"],
                        student["Class"]
                    ))
                break
        if self.Looting:
            for item in output:
                self.Loot.AddLoot(item)
        return output

    def GetHomeworksIDs(self) -> list[str]:
        output = []
        try:
            response = self.Session.get(self.Server.GetEndpoint("homeworks"))
        except requests.exceptions.RequestException as e:
            raise ConnectionException from e
        soup = BeautifulSoup(response.content, "html.parser")
        homeworksList = soup.find(id="grdukoly_DXMainTable")("tr", recursive=False)
        for homeworkRow in homeworksList[1:]: # První je hlavička tabulky (normálně bych se divil, proč tu není <thead> a <tbody> (jako u jiných tabulek), ale jsou to Bakaláři, takže to jsem schopnej pochopit)
            output.append(homeworkRow("td", recursive=False)[-1].find("span")["target"])
        return output
    def MarkHomeworkAsDone(self, homeworkID: str, studentID: str, state: bool = True):
        """
        Varování: Nepoužívat! Tato metoda je zde jen dočasně (a kvůli testování exploitu)
        Označí daný úkol jako hotový.
        """
        response = self.Session.post(self.Server.GetEndpoint("homeworks_done"), json={
            "homeworkId": homeworkID,
            "completed": state,
            "studentId": studentID
        })
        return response.content
        # if not response["d"]:
        #     warnings.warn(f"Při potvrzování zprávy nebylo vráceno 'true', ale '{response['d']}'; Pravděpodobně nastala chyba; Celý objekt: {response}", UnexpectedBehaviour)

    def GetHomeworks(self, all: bool = False) -> list[Homework]:
        output = []
        driver = self.Selenium_Get()
        driver.get(self.Server.GetEndpoint("homeworks"))
        driver.find_element_by_xpath("//span[span/input[@id='cphmain_cbUnfinishedHomeworks_S']]").click()
        # Proč jsem musel šáhnout po XPath? Protože Bakaláři :) Input, podle kterého to můžeme najít, tak je schovaný...
        # A jeho parrent taky... A protože je to schovaný, tak s tím nemůžeme iteragovat... Takže potřebujeme parrenta
        # parrenta toho input, který už vidět je a můžeme na něj kliknout :)

        #TODO: all

        # Vytáhnout zdroj
        source = driver.page_source

        # Parsnout a extahovat do class
        soup = BeautifulSoup(source, "html.parser")
        rows = soup.find(id="grdukoly_DXMainTable").find("tbody")("tr", recursive=False)
        for row in rows[1:]: # První je hlavička tabulky (normálně bych se divil, proč tu není <thead> a <tbody> (jako u jiných tabulek), ale jsou to Bakaláři, takže to jsem schopnej pochopit)
            tds = row("td")
            datumOdevzdani = datetime.strptime(tds[0].find("div")("div")[1].text.strip(), "%d. %m.")
            predmet = tds[1].text
            zadani = tds[2].text
            datumZadani = datetime.strptime(tds[3].text.strip(), "%d. %m.") # Asi bude potřebovat stripnout
            #TODO: tds[4] = přílohy; tds[4]:
            # <td id="grdukoly_tccell15_4" class="overflowvisible dxgv">
			# 	<div>
			# 	    <span class="message_detail_header_paper_clips_menu attachment_dropdown _dropdown-onhover-target" style="{{if PocetFiles==0 }}visibility: hidden; {{/if}}">
            #             <span class="message_detail_header_paper_clips ico32-data-sponka"></span> <span class="message_detail_header_paper_clips_files dropdown-content left-auto">
            #                 <a href="getFile.aspx?f=agepbdncjdfigmjcifpplpkojmoodnobgnalomephbboehdoicmhbcoeedoicloi" target="_blank">
            #                     <span class="attachment_name">snek.png</span>
            #                     <span class="attachment_size">284 KB</span>
            #                 </a>
			# 		    </span>
			# 		</span>
			# 	</div>
			# </td>


            hotovo = tds[5].find("div").find("input")["value"].lower() == "true"
            ID = tds[-1].find("span")["target"] # = tds[6]

            output.append(Homework(ID, datumOdevzdani, predmet, zadani, datumZadani, hotovo))
            





        # Zkrontrolovat zda je zde ještě další stránka... (možná udělat na začátku a případně ji zvětšit)
        pass



        driver.close()

        return output



    def Selenium_Get(self, login = True) -> webdriver:
        driver = self.Selenium_Create()
        self.Selenium_Login(driver)
        return driver
    def Selenium_Create(self) -> webdriver:
        if self.Selenium == None:
            raise ValueError("No Selenium handler/settings")
        return self.Selenium.open()
    def Selenium_Login(self, driver: webdriver):
        driver.get(self.Server.GetEndpoint("login"))
        driver.find_element_by_id("username").send_keys(self.User)
        driver.find_element_by_id("password").send_keys(self.Password)
        driver.find_element_by_id("loginButton").click()



class Looting:
    class JSONSerializer(json.JSONEncoder):
        def default(self, object):
            if isinstance(object, datetime):
                return {
                    "_type":   "datetime",
                    "value":    str(object)
                }
            if isinstance(object, BakalariObject):
                output = dict(object.__dict__)
                output["_type"] = type(object).__name__
                if "Instance" in output:
                    del output["Instance"]
                return output
            #raise TypeError()

    def __init__(self):
        self.Data: dict[str, BakalariObject] = {}
        self.IDs: dict[str, BakalariObject] = {}

    def AddLoot(self, object: BakalariObject, skipCheck: bool = False) -> bool:
        """Adds object to loot if it's ID is not already there; Returns True when object is added, False otherwise"""

        if not skipCheck and object.ID in self.IDs:
            return False
        self.Data.setdefault(type(object).__name__, [])
        self.Data[type(object).__name__].append(object)
        self.IDs[object.ID] = object
        return True

    def ToJSON(self, byIDs: bool = False, ensure_ascii: bool = False):
        return self.JSONSerializer(ensure_ascii = ensure_ascii).encode(self.IDs if byIDs else self.Data)

    def FromJSON(self, jsonString: str, skipCheck: bool = False):
        parsed = json.loads(jsonString)
        module = __import__(__name__)

        def Recursion(data) -> object:
            for index, value in (enumerate(data) if isinstance(data, list) else data.items()):
                #print(f"Enumerating index '{index}', value: {value}")
                if isinstance(value, list) or isinstance(value, dict):
                    data[index] = Recursion(value)
            if isinstance(data, dict) and "_type" in data:
                if data["_type"] == "datetime":
                    data = String2Datetime(data["value"])
                else:
                    if not hasattr(module, data["_type"]):
                        raise TypeError("Unknown type to load; Type: " + data["_type"])
                    class_constructor = getattr(module, data["_type"])
                    signature = inspect.signature(class_constructor)
                    supply_list = []
                    for param in signature.parameters:
                        param = First2Upper(param.lstrip("_"))
                        # print(f"Trying to add '{param}'...")
                        if param in data:
                            supply_list.append(data[param])
                            # print(f"Added '{param}' with value '{data[param]}'")
                    # print(f"In signature: {len(signature.parameters)}; In supply_list: {len(supply_list)}")
                    data = class_constructor(*supply_list)
                    #print("Adding new object to Loot (" + class_constructor.__name__ + ")")
                    self.AddLoot(data, skipCheck)
            return data
        
        parsed = Recursion(parsed)

