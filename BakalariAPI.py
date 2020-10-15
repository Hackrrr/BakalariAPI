"""Rádoby 'API' pro Bakaláře (resp. spíše scraper než API)"""
from __future__ import annotations
import warnings
from datetime import datetime, timedelta
import json
import re
import requests                         # Install
from bs4 import BeautifulSoup           # Install
# Not yet... Install html5lib

import Exceptions



Endpoints = {
    "login":            "/login",
    "logout":           "/logout",
    "dashboard":        "/dashboard",
    "komens":           "/next/komens.aspx",
    "komens_get":       "/next/komens.aspx/GetMessageData",
    "komens_confirm":   "/next/komens.aspx/SetMessageConfirmed",
    "file":             "/next/getFile.aspx",
    "grades":           "/next/prubzna.aspx",
    "session_info":     "/sessioninfo",
    "session_extend":   "/sessionextend",
    "meetings":         "/Collaboration/OnlineMeeting/MeetingsOverview",
    "meetings_info":    "/Collaboration/OnlineMeeting/Detail"
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
    #TODO: Wrapping?
    for br in soup("br"):
        br.replace_with("\n" + br.text)

    body = soup.find("body")
    if body != None:
        soup = body
    
    return soup.get_text().strip()

# Odstraněno... soup.get_text() dělá "potřebné" bezpečněji... (prostě místo tohohle volej na soupu .get_text() :) )
# def RemoveMicrosoftTeamsFooter(text: str, quiet: bool = False) -> str:
#     """Stripne Miscrosoft Teams footer; Viz poznámky dál
#     Tahle funkce hrubě tipuje... Provádí se ověření jen vůči jednomu divu a odsekne se vše dál
#     Takže použít jen v případech, kdy na 100% je jistý, že tam ten footer je
#     """
#     positions = FindAll(text, '<div style="width:100%; height:20px"><span style="white-space:nowrap; color:gray; opacity:.36">________________________________________________________________________________</span>', False)
#     if len(positions) < 2:
#         if not quiet:
#             warnings.warn("It seems that there is no footer to remove", Exceptions.UnexpectedBehaviour)
#         return text
#     return text[:positions[len(positions) - 2]]


class Server:
    """Třída/objekt držící informace o serveru na kterém běží Bakaláři"""
    def __init__(self, url: str):
        if (not IsHTTPScheme(url)):
            raise Exceptions.InputException
        self.Url: str = url
    
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

class KomensFile:
    """Třída/objekt držící informace o Komens souboru/příloze na Bakalařích"""
    def __init__(self, ID: str, name: str, size: int, type: str, komensID: str, path: str, instance: BakalariAPI = None):
        self.ID: str = ID
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
        return self.Instance.server.GetEndpoint("file") + "?f=" + self.ID
    def DownloadStream(self) -> requests.Response:
        """Otevře stream na pro daný soubor pomocí 'requests' modulu a vrátí requests.Response, kterým lze iterovat pomocí metody '.iter_lines()'"""
        self.Instance.session.get(self.GenerateURL(), stream=True)
    def Download(self) -> bytes:
        """Stáhne daný soubor a vrátí ho jakožto (typ) byty (Doporučuje se ale použít metoda '.DownloadStream()', jelikož se zde soubor ukládá do paměti a ne na disk)"""
        return self.Instance.session.get(self.GenerateURL()).content

class Komens:
    """Třída/objekt držící informace o Komens (zprávě/zprách)"""
    # Od, Zpráva, kdy, potvrdit, byla potvrzena?, "typ"
    def __init__(self, ID: str, sender: str, content: str, time: str, confirm: bool, confirmed: bool, type: str, readed: bool, files: list[KomensFile] = None, instance: BakalariAPI = None):
        self.ID: str = ID
        self.Sender: str = sender
        self.Content: str = content
        self.Time: datetime = datetime.strptime(time, "%d.%m.%Y %H:%M") #TODO: Parse it outside
        self.NeedsConfirm: bool = confirm
        self.Confirmed: bool = confirmed
        self.Type: str = type
        self.Readed: bool = readed
        self.Files: list[KomensFile] = files
        self.Instance: BakalariAPI = instance
    def __eq__(self, other: Komens):
        return self.ID == other.ID
    # @property
    # def Content(self) -> str:
    #     return BeautifulSoup(self.RawContent, "html.parser").prettify()
    def Confirm(self): #TODO: Some how refractor this...
        response = self.Instance.session.post(self.Instance.server.GetEndpoint("komens_confirm"), json={
            "idmsg": self.ID
        }).json()
        if not response["d"]:
            warnings.warn(f"Při potvrzování zprávy nebylo vráceno 'true', ale '{response['d']}'; Pravděpodobně nastala chyba; Celý objekt: {response}", Exceptions.UnexpectedBehaviour)
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

class Grade:
    """Třída/objekt držící informace o Známkách/Klasifikaci"""
    def __init__(self, ID: str, subject: str, grade: str, weight: int, name: str, note1: str, note2: str, date1: str, date2: str, orderInClass: str, type: str, new: bool):
        self.ID: str = ID
        self.Subject: str = subject
        self.Grade: str = grade
        self.Weight: int = weight
        self.Name: str = name
        self.Note1: str = note1
        self.Note2: str = note2
        self.Date1: datetime = datetime.strptime(date1, "%d.%m.%Y") #TODO: Parse it outside
        self.Date2: datetime = datetime.strptime(date2, "%d.%m.%Y") #TODO: Parse it outside
        self.Order: str = orderInClass
        self.Type: str = type
        self.New: bool = new #TODO: Remove this?
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

class Meeting:
    """Třída/objekt držící informace o Známkách/Klasifikaci"""                                                                                                                          # ID + time
    def __init__(self, ID: str, ownerID: str, name: str, content: str, startTime: datetime, endTime: datetime, joinURL: str, participants: list[tuple[str, str]], participantsReadInfo: list[tuple[str, datetime]]):
        self.ID: str = ID
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



"""
Pokud najdu JSON i učitelů, tak mergnu do class Osoba ze které budou derivovat studen a učitel/personál
"""
class Student:
    """Třída/objekt držící informace o studentovy"""
    def __init__(self, ID: str, name: str, surname: str, _class: str):
        self.ID: str = ID
        self.Name: str = name
        self.Surname: str = surname
        self.Class: str = _class
    def __eq__(self, other: Student):
        return self.ID == other.ID
    def Format(self) -> str:
        return f"{self.ID}: {self.Name} {self.Surname} ({self.Class})"


class BakalariAPI:
    """Třída/objekt který obsluhuje ostatní komponenty"""
    Students: list[Student] = []
    #TODO: Ukládat výsledky všeho pokud "self.loot"

    def __init__(self, server: Server, user: str, password: str, login: bool = True, loot: bool = True):
        self.server: Server = server
        self.user: str = user
        self.password: str = password
        self.session: requests.Session = requests.Session()
        self.loot: bool = loot
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


    def GetGrades(self, fromData: datetime = None) -> list[Grade]:
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
    def GetAllGrades(self) -> list[Grade]:
        return self.GetGrades(datetime(1, 1, 1))

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

    def GetMettingsIDs(self) -> list[str]:
        output = []
        response = self.session.get(self.server.GetEndpoint("meetings"))
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
            elif self.loot and line.startswith("model.Students = ko.mapping.fromJS("):
                loot["Students"] = True
                studentsJSON = json.loads(line.strip()[len("model.Students = ko.mapping.fromJS("):-2])
                for student in studentsJSON:
                    BakalariAPI.Students.append(Student(
                        student["Id"],
                        student["Name"],
                        student["Surname"],
                        student["Class"]
                    ))
            if loot["Meetings"] and (not self.loot or loot["Students"]):
                break
        return output
    #TODO: Filtr MettingsIDs ((všechny/aktivní) | (od, do) | ...)
    def GetMeeting(self, ID: str) -> Meeting:
        response = self.session.get(self.server.GetEndpoint("meetings_info") + "/" + ID).json()
        return Meeting(
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