"""Rádoby 'API' pro Bakaláře (resp. spíše scraper než API)"""
from __future__ import annotations
import warnings
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
import json
import re
import inspect
import requests                         # Install
from bs4 import BeautifulSoup           # Install

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


LAST_SUPPORTED_VERSION = "1.35.1023.2"


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
    "user_info":            "/next/osobni_udaje.aspx"
}



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
    
    @abstractmethod
    def Format(self) -> str:
        pass
    

class KomensFile(BakalariObject):
    """Třída/objekt držící informace o Komens souboru/příloze na Bakalařích"""
    def __init__(self, ID: str, name: str, size: int, type: str, komensID: str, path: str, instance: BakalariAPI = None):
        super(KomensFile, self).__init__(ID)
        self.Name: str = name
        self.Size: int = size
        self.Type: str = type
        self.KomensID: str = komensID
        self.Path: str = path
        self.Instance: BakalariAPI = instance
    def __eq__(self, other: KomensFile):
        return self.ID == other.ID
    def GenerateURL(self):
        """Generuje (Sestaví) URL k souboru na serveru (SeverURL + Endpoint + ID_SOUBORU)"""
        return self.Instance.Server.GetEndpoint("file") + "?f=" + self.ID
    def DownloadStream(self) -> requests.Response:
        """Otevře stream na pro daný soubor pomocí 'requests' modulu a vrátí requests.Response, kterým lze iterovat pomocí metody '.iter_lines()'"""
        self.Instance.Session.get(self.GenerateURL(), stream=True)
    def Download(self) -> bytes:
        """Stáhne daný soubor a vrátí ho jakožto (typ) byty (Doporučuje se ale použít metoda '.DownloadStream()', jelikož se zde soubor ukládá do paměti a ne na disk)"""
        return self.Instance.Session.get(self.GenerateURL()).content
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
    def __eq__(self, other: Komens):
        return self.ID == other.ID
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
    def __eq__(self, other: Grade):
        return self.ID == other.ID
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
    def __eq__(self, other: Student):
        return self.ID == other.ID
    def Format(self) -> str:
        return f"{self.ID}: {self.Name} {self.Surname} ({self.Class})"



class BakalariAPI:
    """Třída/objekt který obsluhuje ostatní komponenty"""
    def __init__(self, server: Server, user: str, password: str, login: bool = True, looting: bool = True):
        self.Server: Server = server
        self.User: str = user
        self.Password: str = password
        self.Session: requests.Session = requests.Session()
        self.Looting: bool = looting
        self.Loot: Looting = Looting() if self.Looting else None
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
                    self
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

