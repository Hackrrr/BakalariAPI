"""
Modul obsahující většinu objektů z BakalariAPI.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from bs4 import BeautifulSoup

from .bakalari import BakalariAPI, Endpoint, RequestsSession
from .utils import bs_get_text

__all__ = [
    "ServerInfo",
    "UserInfo",

    "BakalariObject",
    "BakalariFile",
    "KomensFile",
    "HomeworkFile",
    "Komens",
    "Grade",
    "Meeting",
    "Student",
    "Homework",
]

class ServerInfo():
    """    Třída obsahující informace o samotném systému Bakaláři.

    Atributy:
        version:
            Verze Bakalářů.
        version_date:
            Datum verze Bakalářů.
        evid_number:
            Evidenční číslo verze Bakalářů.
    """
    def __init__(self, bakalariVersion: str = "", bakalariVersionDate: datetime = None, bakalariEvidNumber: int = None):
        self.version: str = bakalariVersion
        self.version_date: datetime = bakalariVersionDate
        self.evid_number: int = bakalariEvidNumber
class UserInfo():
    """    Třída obsahující informace o uživatelovi.

    Atributy:
        type:
            Typ uživatele.
            #TODO: Enum?
        hash:
            Hash uživatele.
        ID:
            ID uživatele, poukd již bylo nalezeno (jinak prázdný string).
            Pozn.: Jelikož zatím bylo manipulováno jen se studenkstým účtem, jedná se o ID studenta. Je ale možné, že ostatní typy účtů (učitelé) ID nemají.
    """
    def __init__(self, userType: str = "", userHash: str = "", userID: str = ""):
        self.type: str = userType
        self.hash: str = userHash
        self.ID: str = userID

class BakalariObject(ABC):
    """    Základní třída pro objekty parsované z Bakalářů (kromě tříd ServerInfo a UserInfo).

    Atributy:
        ID:
            ID objektu.
            Slouží k jednoznačné identifikaci objektu v rámci Bakalářů.
    """
    def __init__(self, ID: str):
        self.ID = ID
    @abstractmethod
    def format(self) -> str:
        """Vrátí text vhodný pro zobrazení uživatelovi aplikace/BakalariAPI."""
        pass

class BakalariFile(BakalariObject):
    """Třída/objekt držící informace o souboru/příloze na Bakalařích"""
    def __init__(self, ID: str, name: str, size: int, type_: str = ""):
        super(BakalariFile, self).__init__(ID)
        self.name: str = name
        self.size: int = size
        self.type: str = type_

    @property
    def downloadURL(self, bakalariAPI: BakalariAPI):
        """Generuje (Sestaví) URL k souboru na serveru (SeverURL + Endpoint + ID_SOUBORU)"""
        return bakalariAPI.get_endpoint(Endpoint.FILE) + "?f=" + self.ID

    # def DownloadStream(self, instance: BakalariAPI) -> requests.Response:
    #     """Otevře stream na pro daný soubor pomocí 'requests' modulu a vrátí requests.Response, kterým lze iterovat pomocí metody '.iter_lines()'"""
    #     instance.Session.get(self.GenerateURL(instance.server), stream=True)
    #TODO: DowloadStream

    def download(self, bakalariAPI: BakalariAPI) -> bytes:
        """Stáhne daný soubor a vrátí ho jakožto (typ) byty (Doporučuje se ale použít metoda '.DownloadStream()', jelikož se zde soubor ukládá do paměti a ne na disk)"""
        return bakalariAPI.session_manager.get_session_or_create(RequestsSession).get(self.downloadURL).content

    def format(self) -> str:
        return (
            f"ID: {self.ID}\n"
            f"Název souboru: {self.name}\n"
            f"Typ: {self.type}\n"
            f"Velikost: {self.size}"
        )
class KomensFile(BakalariFile):
    """Třída/objekt držící informace o Komens souboru/příloze na Bakalařích"""
    def __init__(self, ID: str, name: str, size: int, type_: str, komensID: str, path: str):
        super().__init__(ID, name, size, type_)
        self.komensID: str = komensID
        self.path: str = path
    def format(self) -> str:
        return (
            f"ID: {self.ID}\n"
            f"Název souboru: {self.name}\n"
            f"Typ: {self.type}\n"
            f"Velikost: {self.size}\n"
            f"ID přidružené zprávy: {self.komensID}\n"
            f"(Nepoužitelná) Cesta: {self.path}\n"
        )
class HomeworkFile(BakalariFile):
    """Třída/objekt držící informace o souboru/příloze k úkolu na Bakalařích"""
    def __init__(self, ID: str, name: str, homeworkID: str):
        super().__init__(ID, name, None, None)
        self.homeworkID: str = homeworkID
    def format(self) -> str:
        return (
            f"ID: {self.ID}\n"
            f"Název souboru: {self.name}\n"
            f"ID přidruženého úkolu: {self.homeworkID}\n"
        )

class Komens(BakalariObject):
    """Třída/objekt držící informace o Komens (zprávě/zprách)"""
    def __init__(self, ID: str, sender: str, content: str, time: datetime, confirm: bool, confirmed: bool, type_: str, files: list[KomensFile] = None):
        super().__init__(ID)
        self.sender: str = sender
        self.content: str = content
        self.time: datetime = time
        self.need_confirm: bool = confirm
        self.confirmed: bool = confirmed
        self.type: str = type_
        self.files: list[KomensFile] = files
    def confirm(self, bakalariAPI: BakalariAPI):
        """Potvrdí přečtení"""
        bakalariAPI.session_manager.get_session_or_create(RequestsSession).post(bakalariAPI.get_endpoint(Endpoint.KOMENS_CONFIRM), json={
            "idmsg": self.ID
        }).json() # Jakože tohle jen jen ztráta výkonu... Actually to nemusíme vůbec parsovat...
    def format(self) -> str:
        return (
            f"ID: {self.ID}\n"
            f"Od: {self.sender}\n"
            f"Datum: {self.time.strftime('%d. %m. %Y, %H:%M')}\n"
            f"Vyžaduje potvrzení? {'Ano' if self.need_confirm else 'Ne'}; Potvrzena? {'Ano' if self.confirmed else 'Ne'}\n"
            f"Má soubory? {'Ano' if len(self.files) > 0 else 'Ne'}\n"
            "\n"
            f"{bs_get_text(BeautifulSoup(self.content, 'html.parser'))}" #.get_text().strip()
        )

class Grade(BakalariObject):
    """Třída/objekt držící informace o Známkách/Klasifikaci"""
    def __init__(self, ID: str, subject: str, grade: str, weight: int, name: str, note1: str, note2: str, date1: datetime, date2: datetime, order_in_class: str, type_: str):
        super().__init__(ID)
        self.subject: str = subject
        self.grade: str = grade
        self.weight: int = weight
        self.name: str = name
        self.note1: str = note1
        self.note2: str = note2
        self.date1: datetime = date1
        self.date2: datetime = date2
        self.order_in_class: str = order_in_class
        self.type: str = type_
    def format(self):
        return (
            f"ID: {self.ID}\n"
            f"Předmět: {self.subject}\n"
            f"Název: {self.name}\n"
            f"Hodnota: {self.grade}\n"
            f"Váha: {self.weight}\n"
            f"Datum: {self.date1.strftime('%d. %m. %Y')}\n"
            f"Poznámka 1: {self.note1.strip()}\n"
            f"Poznámka 2: {self.note2.strip()}"
        )

class Meeting(BakalariObject):
    """Třída/objekt držící informace o známkách/klasifikaci"""                                                                                                                                        # ID + time
    def __init__(self, ID: str, ownerID: str, name: str, content: str, start_time: datetime, end_time: datetime, joinURL: str, participants: list[tuple[str, str]], participants_read_info: list[tuple[str, datetime]]):
        super().__init__(ID)
        self.ownerID: str = ownerID
        self.name: str = name
        self.content: str = content
        self.start_time: datetime = start_time
        self.end_time: datetime = end_time
        self.joinURL: str = joinURL
        self.participants: list[tuple[str, str]] = participants # ID, (Celé) Jméno
        self.participants_read_info: list[tuple[str, datetime]] = participants_read_info # ID, Čas přečtení
    @property
    def owner_name(self):
        """Jméno pořadatele schůzky"""
        for participant in self.participants:
            if participant[0] == self.ownerID:
                return participant[1]
    def format(self) -> str:
        return (
            f"ID: {self.ID}\n"
            f"Pořadatel: {self.owner_name}\n"
            f"Začátek: {self.start_time.strftime('%H:%M, %d. %m. %Y')}\n"
            f"Konec:   {self.end_time.strftime('%H:%M, %d. %m. %Y')}\n"
            f"URL na připojení: {self.joinURL}\n"
            f"Název: {self.name.strip()}\n"
            "\n"
            f"{bs_get_text(BeautifulSoup(self.content, 'html.parser'))}"
        )

class Student(BakalariObject):
    """Třída/objekt držící informace o studentovy"""
    def __init__(self, ID: str, name: str, surname: str, class_: str):
        super().__init__(ID)
        self.name: str = name
        self.surname: str = surname
        self.class_: str = class_
    def format(self) -> str:
        return f"{self.ID}: {self.name} {self.surname} ({self.class_})"

class Homework(BakalariObject):
    """Třída/objekt držící informace o domacím úkolu"""
    def __init__(self, ID: str, submission_date: datetime, subject: str, content: str, assignment_date: datetime, done: bool, files: list[HomeworkFile] = []):
        super().__init__(ID)
        self.submission_date: datetime = submission_date
        self.subject: str = subject
        self.content: str = content
        self.assignment_date: datetime = assignment_date
        self.done: bool = done
        self.files: list[HomeworkFile] = files
    def mark_as_done(self, bakalariAPI: BakalariAPI, value: bool = True):
        """Označí úkol jako hotový"""
        bakalariAPI.session_manager.get_session_or_create(RequestsSession).post(bakalariAPI.get_endpoint(Endpoint.HOMEWORKS_DONE), json={
            "homeworkId": self.ID,
            "completed": value
            #"studentId": studentID
        })
    def format(self) -> str:
        return (
            f"ID: {self.ID}\n"
            f"Datum odevzdaní: {self.submission_date.strftime('%d. %m.')}\n"
            f"Datum zadání: {self.assignment_date.strftime('%d. %m.')}\n"
            f"Předmět: {self.subject}\n"
            f"Hotovo? {'Ano' if self.done else 'Ne'}\n"
            f"Má soubory? {'Ano' if len(self.files) > 0 else 'Ne'}\n"
            "\n"
            f"{bs_get_text(BeautifulSoup(self.content, 'html.parser'))}"
        )
