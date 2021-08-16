"""Modul obsahující většinu objektů z BakalariAPI."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from typing import Generic, TypeVar

from bs4 import BeautifulSoup

from .bakalari import BakalariAPI, Endpoint
from .serialization import Serializable
from .sessions import RequestsSession
from .utils import T0, bs_get_text, cs_timedelta, get_full_type_name, resolve_string

__all__ = [
    "ServerInfo",
    "UserInfo",
    "BakalariObject",
    "BakalariObj",
    # "BakalariObj_co",
    "UnresolvedID",
    "BakalariFile",
    "KomensFile",
    "HomeworkFile",
    "Komens",
    "Grade",
    "MeetingProvider",
    "Meeting",
    "Student",
    "Homework",
]


class ServerInfo:
    """Třída obsahující informace o samotném systému Bakaláři.

    Atributy:
        url:
            URL adresa webového rozhraní Bakalářů.
            Musí být ve validním HTTP scématu, např. "https://bakalari.mojeskola.cz".
        version:
            Verze Bakalářů.
        version_date:
            Datum verze Bakalářů.
        evid_number:
            Evidenční číslo verze Bakalářů.
    """

    def __init__(
        self,
        url: str | None = None,
        bakalariVersion: str | None = None,
        bakalariVersionDate: datetime | None = None,
        bakalariEvidNumber: int | None = None,
    ):
        self.url: str | None = url
        self.version: str | None = bakalariVersion
        self.version_date: datetime | None = bakalariVersionDate
        self.evid_number: int | None = bakalariEvidNumber


class UserInfo:
    """Třída obsahující informace o uživatelovi.

    Atributy:
        type:
            Typ uživatele.
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


class BakalariObject(Serializable[dict], ABC):
    """Základní třída pro objekty parsované z Bakalářů (kromě tříd ServerInfo a UserInfo).

    Atributy:
        ID:
            ID objektu.
            Slouží k jednoznačné identifikaci objektu v rámci Bakalářů.
    """

    def __init__(self, ID: str):
        self.ID = ID

    @abstractmethod
    def format(self, rich_colors: bool = False) -> str:
        """Vrátí text vhodný pro zobrazení uživatelovi aplikace/BakalariAPI.

        Args:
            rich_colors:
                Indikuje, zda ve výsledném textu mají být zahnuty "tagy" barev (pro `rich` modul).
                Pokud `True`, "tagy" budou přítomny, jinak ne.
        """

    def serialize(self) -> dict:
        return dict(self.__dict__)

    @classmethod
    def deserialize(cls: type[T0], data: dict) -> T0:
        # Postaveno na základě tohoto https://stackoverflow.com/a/2169191
        obj = super().__new__(cls)  # type: ignore # https://github.com/python/mypy/issues/9282

        for k, v in data.items():
            # if hasattr(obj, k): # Nebude fungovat, jelikož novoláme __init__, nýbrž pouze __new__ a tím pádem objekt nemá prakticky žádné atributy
            setattr(obj, k, v)
        return obj


BakalariObj = TypeVar("BakalariObj", bound=BakalariObject)
# BakalariObj_co = TypeVar("BakalariObj_co", bound=BakalariObject, covariant=True) Možná někdy, až budu vnímat 3 další dimenze, tak to zprovozním...


class UnresolvedID(BakalariObject, Generic[BakalariObj]):
    """Třída/objekt držící ID, které bylo získáno, ale zatím k němu nebyl získán objekt.

    Atributy:
        type:
            Odhadovaný typ objektu, pro které je toto ID
    """

    def __init__(self, ID: str, type_: type[BakalariObj]):
        super().__init__(ID)
        self.type: type[BakalariObj] = type_

    def format(self, rich_colors: bool = False) -> str:
        return f"Nevyřešené ID '{self.ID}'" + (
            "" if self.type is None else " typu {self.type}"
        )

    def serialize(self) -> dict:
        output = super().serialize()
        output["type"] = get_full_type_name(self.type)
        return output

    @classmethod
    def deserialize(cls: type[T0], data: dict) -> T0:  # type: ignore # Rád bych to odsoudil jako mypy bug, ale nemůžu nic najít
        # Dle mého je tenhle "type: ignore" (↑) v pořádku, ale vážně nevím, protože jsem nenašel žádný issue v mypy
        # repu, který by řešil (přímo) tento případ (Generic(/Protocol)->Non generic->Generic)
        output = super().deserialize.__func__(cls, data)  # type: ignore # https://github.com/python/mypy/issues/9282
        output.type = resolve_string(data["type"])
        return output


class BakalariFile(BakalariObject):
    """Třída/objekt držící informace o souboru/příloze na Bakalařích"""

    def __init__(self, ID: str, name: str, size: int, type_: str = ""):
        super().__init__(ID)
        self.name: str = name
        self.size: int = size
        self.type: str = type_

    def get_download_url(self, bakalariAPI: BakalariAPI):
        """Vygeneruje/Sestaví URL k souboru"""
        return bakalariAPI.get_endpoint(Endpoint.FILE) + "?f=" + self.ID

    def download(self, bakalariAPI: BakalariAPI) -> bytes:
        """Stáhne daný soubor a navrátí ho.
        Pozn.:
            Přestože soubory budou většinou do 10 MB, nedoporučuje se tuto metodu používat pokud si nejste vědomy velikosti souboru.
            Soubor se totiž bufferuje celý a hrozí riziko zaplnění paměti.
            Ideální cesta je napsat vlastní metodu, která bude soubor stahovat po částech a rovnou někam ukládat.
        """
        with bakalariAPI.session_manager.get_session_or_create(
            RequestsSession
        ) as session:
            output = session.get(self.get_download_url(bakalariAPI)).content
        return output

    def format(self, rich_colors: bool = False) -> str:
        return (
            f"ID: {self.ID}\n"
            f"Název souboru: {self.name}\n"
            f"Typ: {self.type}\n"
            f"Velikost: {self.size}"
        )


class KomensFile(BakalariFile):
    """Třída/objekt držící informace o Komens souboru/příloze na Bakalařích"""

    def __init__(
        self, ID: str, name: str, size: int, type_: str, komensID: str, path: str
    ):
        super().__init__(ID, name, size, type_)
        self.komensID: str = komensID
        self.path: str = path

    def format(self, rich_colors: bool = False) -> str:
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
        super().__init__(ID, name, 0, "")
        self.homeworkID: str = homeworkID

    def format(self, rich_colors: bool = False) -> str:
        return (
            f"ID: {self.ID}\n"
            f"Název souboru: {self.name}\n"
            f"ID přidruženého úkolu: {self.homeworkID}\n"
        )


class Komens(BakalariObject):
    """Třída/objekt držící informace o Komens (zprávě/zprách)"""

    def __init__(
        self,
        ID: str,
        sender: str,
        content: str,
        time: datetime,
        confirm: bool,
        confirmed: bool,
        type_: str,
        files: list[KomensFile],
    ):
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
        bakalariAPI.session_manager.get_session_or_create(RequestsSession).post(
            bakalariAPI.get_endpoint(Endpoint.KOMENS_CONFIRM), json={"idmsg": self.ID}
        ).json()  # Jakože tohle jen jen ztráta výkonu... Actually to nemusíme vůbec parsovat...

    def format(self, rich_colors: bool = False) -> str:
        return (
            f"ID: {self.ID}\n"
            f"Od: {self.sender}\n"
            f"Datum: {self.time.strftime('%d. %m. %Y, %H:%M')}\n"
            f"{'[yellow]' if rich_colors and self.need_confirm and not self.confirmed else ''}Vyžaduje potvrzení? {'Ano' if self.need_confirm else 'Ne'}; Potvrzena? {'Ano' if self.confirmed else 'Ne'}{'[/yellow]' if rich_colors and self.need_confirm and not self.confirmed else ''}\n"
            f"Má soubory? {'Ano' if len(self.files) > 0 else 'Ne'}\n"
            "\n"
            f"{bs_get_text(BeautifulSoup(self.content, 'html.parser'))}"  # .get_text().strip()
        )


class Grade(BakalariObject):
    """Třída/objekt držící informace o Známkách/Klasifikaci"""

    def __init__(
        self,
        ID: str,
        subject: str,
        grade: str,
        weight: int,
        name: str,
        note1: str,
        note2: str,
        date1: datetime,
        date2: datetime,
        order_in_class: str,
        type_: str,
    ):
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

    def format(self, rich_colors: bool = False):
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


class MeetingProvider(Serializable):
    """Třída/objekt držící platformě/poskytovatelovi schůzky"""

    BY_ID: dict[int, MeetingProvider] = {}
    BY_KEY: dict[str, MeetingProvider] = {}

    def __init__(self, ID: int, key: str, label: str):
        self.ID: int = ID
        self.key: str = key
        self.label: str = label
        self.BY_ID[self.ID] = self
        self.BY_KEY[self.key] = self

    def serialize(self) -> int:
        return self.ID

    @classmethod
    def deserialize(cls, data: int) -> MeetingProvider:
        return MeetingProvider.BY_ID[data]


MeetingProvider(0, "None", "žádný")
MeetingProvider(1, "Microsoft", "Microsoft Office 365 for Education")
MeetingProvider(2, "Google", "Google Meet")


class Meeting(BakalariObject):
    """Třída/objekt držící informace o známkách/klasifikaci.

    Datetime instance v této tříde jsou offset-aware."""

    def __init__(
        self,
        # Actually je to int, ale všechny ostaní IDčka jsou string, takže se budeme tvářit že je string i tohle...
        ID: str,
        ownerID: str,
        name: str,
        content: str,
        start_time: datetime,
        end_time: datetime,
        join_url: str,
        participants: list[tuple[str, str]],
        participants_read_info: list[tuple[str, datetime]],
        provider: MeetingProvider,
    ):
        super().__init__(ID)
        self.ownerID: str = ownerID
        self.name: str = name
        self.content: str = content
        self.start_time: datetime = start_time
        self.end_time: datetime = end_time
        self.join_url: str = join_url
        self.participants: list[tuple[str, str]] = participants  # ID, (Celé) Jméno
        self.participants_read_info: list[
            tuple[str, datetime]
        ] = participants_read_info  # ID, Čas přečtení
        self.provider: MeetingProvider = provider

    @property
    def owner_name(self) -> str:
        """Jméno pořadatele schůzky."""
        for participant in self.participants:
            if participant[0] == self.ownerID:
                return participant[1]
        return ""

    @property
    def start_time_delta(self) -> timedelta:
        """Vypočte timedeltu do začátku schůzky."""
        return self.start_time - datetime.now(timezone.utc).astimezone()

    @property
    def is_before_start(self) -> bool:
        return datetime.now(timezone.utc).astimezone() < self.start_time

    def format(self, rich_colors: bool = False) -> str:
        delta = self.start_time_delta
        color = ""
        if rich_colors:
            is_before = self.is_before_start
            if not is_before and delta <= timedelta(hours=1):
                color = "red"
            elif is_before and delta <= timedelta(minutes=5):
                color = "yellow"
            elif is_before and delta <= timedelta(minutes=30):
                color = "green"
        return (
            f"ID: {self.ID}\n"
            f"Pořadatel: {self.owner_name}\n"
            f"Začátek: {('[' + color + ']') if rich_colors else ''}{self.start_time.strftime('%H:%M, %d. %m. %Y')}{(' (' + cs_timedelta(delta, 'dhm') + ' do začátku)') if delta > timedelta(0) else (' (začíná nyní)' if delta == timedelta(0) else '')}{('[/' + color + ']') if rich_colors else ''}\n"
            f"Konec:   {self.end_time.strftime('%H:%M, %d. %m. %Y')}\n"
            f"Poskytovatel schůzky: {self.provider.label}\n"
            f"URL na připojení: {self.join_url}\n"
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

    def format(self, rich_colors: bool = False) -> str:
        return f"{self.ID}: {self.name} {self.surname} ({self.class_})"


class Homework(BakalariObject):
    """Třída/objekt držící informace o domacím úkolu"""

    def __init__(
        self,
        ID: str,
        submission_date: datetime,
        subject: str,
        content: str,
        assignment_date: datetime,
        done: bool,
        files: list[HomeworkFile] | None = None,
    ):
        super().__init__(ID)
        # Pozn.: Data u homework objektů májí správně pouze den a měsíc, jelikož nebyl zjištěn způsob,
        # jak dostat rok (ten je nyní defaultní hodnotou datetime, tedy 1900)
        self.submission_date: datetime = submission_date
        self.subject: str = subject
        self.content: str = content
        self.assignment_date: datetime = assignment_date
        self.done: bool = done
        self.files: list[HomeworkFile] = [] if files is None else files

    def mark_as_done(self, bakalariAPI: BakalariAPI, value: bool = True):
        """Označí úkol jako hotový"""
        bakalariAPI.session_manager.get_session_or_create(RequestsSession).post(
            bakalariAPI.get_endpoint(Endpoint.HOMEWORKS_DONE),
            json={
                "homeworkId": self.ID,
                "completed": value
                # "studentId": studentID
            },
        )

    def format(self, rich_colors: bool = False) -> str:
        if len(self.files) > 0:
            soubory_text = ""
            count = 0
            for soubor in self.files:
                soubory_text += f"  Soubor {count}: {soubor.name}\n"
                count += 1
        else:
            soubory_text = "  Nejsou\n"
        return (
            f"ID: {self.ID}\n"
            # Dále bych napsal něco jako:
            # {(' (do odevzdání zbývá ' + cs_timedelta(delta) + ')') if delta > timedelta(0) else ''}\n"
            # plus bych k tomu přidal i barvičky...
            # ... to ale nelze, protože nemáme rok, tak nevíme, jestli jsme v negativu nabo v pozitivu.
            # Jasně, můžeme to odvodit, ale to dělat nechci.
            f"Datum odevzdaní: {self.submission_date.strftime('%d. %m. %Y')}\n"
            f"Datum zadání: {self.assignment_date.strftime('%d. %m. %Y')}\n"
            f"Předmět: {self.subject}\n"
            f"Hotovo? {'Ano' if self.done else ('[yellow]Ne[/yellow]' if rich_colors else 'Ne') }\n"
            f"Soubory?\n{soubory_text}"
            "\n"
            f"{bs_get_text(BeautifulSoup(self.content, 'html.parser'))}"
        )
