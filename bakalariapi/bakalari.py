"""Hlavní část BakalářiAPI. Tento modul obsahuje většinu věcí z celého BakalářiAPI.

Základem je třída BakalářiAPI, která by měla stačit pro "normální" užití.

Tento modul primárně implementuje:
    BakalariAPI - Základní třída na ovládání celého BakalářiAPI
    SeleniumHandler - "Pomocná" třída pomáhající k ovládání Selenia
    Browser - Enum podporovaných browserů pro Selenium
    Looting - Třída starající se o persistenci, uchování a částečné zpracování výsledků
"""

from __future__ import annotations

import atexit
import json
import sys
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from enum import Enum
from multiprocessing import Lock
from typing import Any, Callable, Generic, Type, TypeVar

import requests
from bs4 import BeautifulSoup

_HAVE_SELENIUM = False
try:
    from selenium import webdriver
    from selenium.webdriver.remote.webdriver import WebDriver
    _HAVE_SELENIUM = True
except ImportError:
    pass

#TODO: logging module

LAST_SUPPORTED_VERSION = "1.39.408.1"

class Browser(Enum):
    """Enum prohlížečů/browserů podporovaných Seleniem"""
    CHROME = 0
    FIREFOX = 1
    EDGE = 2
    SAFARI = 3
    OPERA = 4
    IE = 5
class SeleniumHandler:
    """Třída obsahujcí nastavení pro Selenium.
    """
    def __init__(self, browser: Browser, executable_path: str = "", params: dict = {}):
        if "selenium" not in sys.modules:
            raise ImportError(name="selenium")
        self.browser: Browser = browser
        self.executable_path: str = executable_path
        self.params: dict = params
    def open(self, try_silent: bool = True) -> WebDriver:
        #try_silent = False # DEBUG LINE ONLY - SHOULD BE COMMENTED
        #TODO: Get rid of console logs...
        path = {"executable_path":self.executable_path} if self.executable_path != "" and self.executable_path is not None else {}
        if self.browser == Browser.CHROME:
            options = webdriver.ChromeOptions()
            if try_silent:
                options.set_headless(True)
            driver = webdriver.Chrome(options=options, **path, **self.params)
        elif self.browser == Browser.FIREFOX:
            options = webdriver.FirefoxOptions()
            if try_silent:
                options.set_headless(True)
            driver = webdriver.Firefox(options=options, **path, **self.params)
        elif self.browser == Browser.EDGE:
            driver = webdriver.Edge(**path, **self.params)
        elif self.browser == Browser.SAFARI:
            driver = webdriver.Safari(**path, **self.params)
        elif self.browser == Browser.OPERA:
            driver = webdriver.Opera(**path, **self.params)
        elif self.browser == Browser.IE:
            options = webdriver.IeOptions()
            driver = webdriver.Ie(options=options, **path, **self.params)
        else:
            raise ValueError()
        return driver

class Endpoint():
    """Enum endpointů pro Bakaláře"""
    LOGIN = "/login"
    LOGOUT = "/logout"
    DASHBOARD = "/dashboard"
    KOMENS = "/next/komens.aspx"
    KOMENS_GET = "/next/komens.aspx/GetMessageData"
    KOMENS_CONFIRM = "/next/komens.aspx/SetMessageConfirmed"
    FILE = "/next/getFile.aspx"
    GRADES = "/next/prubzna.aspx"
    SESSION_INFO = "/sessioninfo"
    SESSION_EXTEND = "/sessionextend"
    MEETINGS_OVERVIEW = "/Collaboration/OnlineMeeting/MeetingsOverview"
    MEETINGS_INFO = "/Collaboration/OnlineMeeting/Detail/"
    USER_INFO = "/next/osobni_udaje.aspx"
    HOMEWORKS = "/next/ukoly.aspx"
    HOMEWORKS_DONE = "/HomeWorks/MarkAsFinished"
    _ENDPOINT_DICT = {}
Endpoint._ENDPOINT_DICT = {name:path for name,path in Endpoint.__dict__.items() if not name.startswith("_")} # pylint: disable=protected-access

class ResultSet:
    def __init__(self, loot: BakalariObject | list[BakalariObject] = None):
        self.data: dict[str, list[BakalariObject]] = {}
        if loot is not None:
            self.add_loot(loot)
    def add_loot(self, loot: BakalariObject | list[BakalariObject]) -> ResultSet:
        """Přidá loot do tohoto ResultSetu.

        Args:
            loot:
                Loot, který bude přidán do tohoto ResultSetu.
        """
        if not isinstance(loot, list):
            loot = [loot]
        for o in loot:
            self.data.setdefault(type(o).__name__, []).append(o)
        return self
    def retrieve_type(self, _type: Type[BakalariObj]) -> list[BakalariObj]:
        t = _type.__name__
        if t in self.data:
            return self.data[t] #type: ignore - Pylance nechápe, že bound=BakalariObject znamená, že to vlastně je BakalariObject eShrug
        else:
            return []
        #return self.data[t] if t in self.data else []
    def merge(self, result_set: ResultSet) -> ResultSet:
        for (t, lst) in result_set.data.items():
            self.data[t] = self.data.setdefault(t, []) + lst
        return self
    def remove(self, _type: Type[BakalariObject]) -> ResultSet:
        try:
            del self.data[_type.__name__]
        except KeyError:
            pass
        return self
GetterOutputTypeVar = TypeVar("GetterOutputTypeVar", BeautifulSoup, dict)
class GetterOutput(Generic[GetterOutputTypeVar]):
    def __init__(self, endpoint: str, data: GetterOutputTypeVar):
        self.endpoint: str = endpoint
        self.data: GetterOutputTypeVar = data
        self.type: Type[GetterOutputTypeVar] = type(data) 

class BakalariSession(ABC):
    """Základní (abstraktní) classa pro typy sessionů.

    Definuje základní metody, které musí každý typ mít/implementovat.

    Atributy:
        bakalariAPI:
            Reference k přidružené BakalariAPI instanci, tedy instanci, pro kterou je tato session validní.
        busy:
            Je session zaneprázdněná?
    """
    def __init__(self, bakalariAPI: BakalariAPI, setBusy: bool = True, login: bool = True):
        self.bakalariAPI: BakalariAPI = bakalariAPI
        self.busy: bool = setBusy
        # self.__stop_auto_refresh: bool = False
        if login:
            self.login()

    @abstractmethod
    def get_session_info(self) -> dict:
        pass

    def get_remaining(self) -> int:
        return int(float(self.get_session_info()["remainingTime"])) #Taková cesta, jak převést string float na int :)

    @abstractmethod
    def login(self) -> bool:
        pass

    def is_logged(self) -> bool: #TODO: Můžeme zde, prosím, dostat nějaký elegentní způsob? Ne? Ok, nevermind...; Pravděpodobně nechat na derivujících classách (request a sledovat redirect) (=> abstract method)
        return self.get_remaining() == 0

    @abstractmethod
    def extend(self):
        pass

    @abstractmethod
    def kill(self, nice = True):
        pass

    #def start_extend_loop(self, interval = 60000):
    #TODO: (Start+Stop) Auto refresh method (with multithread)
class RequestsSession(BakalariSession):
    def __init__(self, bakalariAPI: BakalariAPI, setBusy: bool = True, login: bool = True):
        self.session = requests.session()
        super().__init__(bakalariAPI, setBusy, login)
    def extend(self):
        self.session.get(self.bakalariAPI.get_endpoint(Endpoint.SESSION_EXTEND))
    def kill(self, nice = True):
        if nice:
            self.session.get(self.bakalariAPI.get_endpoint(Endpoint.LOGOUT))
        self.session.close()
    def get_session_info(self) -> dict:
        return self.session.get(self.bakalariAPI.get_endpoint(Endpoint.SESSION_INFO)).json()
    def login(self) -> bool:
        return self.session.post(self.bakalariAPI.get_endpoint(Endpoint.LOGIN), {
            "username": self.bakalariAPI.username,
            "password": self.bakalariAPI.password
        }).url != self.bakalariAPI.get_endpoint(Endpoint.LOGIN)
    def is_logged(self) -> bool:
        raise NotImplementedError()

    def get(self, *args, **kwargs) -> requests.Response:
        return self.session.get(*args, **kwargs)
    def post(self, *args, **kwargs) -> requests.Response:
        return self.session.post(*args, **kwargs)
class SeleniumSession(BakalariSession):
    #TODO: Zde mi přijde, že je možná hromada optimalizace - Webdriver můžeme nechat na pokoji a používat jen request modul,
    # abychom nemuseli čekat na webdriver. Teoreticky bychom mohli vytvořit interní RequestSession, kterému by byly přidány jen cookies
    # a přes něj by jsme mohli dělat "util" věci (extend, login, is_logged, ...)
    #BTW Potřebujeme dodělat tuhle classu :)
    def __init__(self, bakalariAPI: BakalariAPI, setBusy: bool = True, login: bool = True):
        if not _HAVE_SELENIUM:
            raise exceptions.NoSeleniumException()
        self.session: WebDriver = bakalariAPI.selenium_handler.open()
        super().__init__(bakalariAPI, setBusy)
        
    def get_session_info(self) -> dict:
        #return json.loads(self.session.get(self.bakalariAPI.get_endpoint(Endpoint.SESSION_INFO)))
        raise NotImplementedError()
    def extend(self):
        self.session.get(self.bakalariAPI.get_endpoint(Endpoint.SESSION_EXTEND))
    def kill(self, nice = True):
        # try:
        if nice:
            self.session.get(self.bakalariAPI.get_endpoint(Endpoint.LOGOUT))
        self.session.close()
        # except WebDriverException: # Kvůli tomu, když nějakým záhadným způsobem je už webdriver mrtvý (resp. zavřený) :)
        #     #No... Dost nepěkné řešení, jelikož tohle chytí úplně všecho, co se pokazí, ale lepší řešení neexistuje eShrug
        #     pass
    def login(self) -> bool:
        self.session.get(self.bakalariAPI.get_endpoint(Endpoint.LOGIN))
        self.session.find_element_by_id("username").send_keys(self.bakalariAPI.username)
        self.session.find_element_by_id("password").send_keys(self.bakalariAPI.password)
        self.session.find_element_by_id("loginButton").click()
        return self.session.current_url != self.bakalariAPI.get_endpoint(Endpoint.LOGIN)
    def is_logged(self) -> bool:
        raise NotImplementedError()
Session = TypeVar("Session", bound=BakalariSession)

class SessionManager:
    """Classa, která spravuje sessiony.

    Atributy:
        bakalariAPI:
            Reference k BakalářiAPI, pro které spravuje sessiony.
        sessions:
            Slovník, který obsahuje všechny sessiony pod správou tohoto SessionMannageru.
            Klič je typ sessionu jako string (tedy název classy sessionu) a hodnota je list sessionů tohoto typu.
    """

    def __init__(self, ref: BakalariAPI):
        self.__lock = Lock()
        self.bakalariAPI: BakalariAPI = ref
        self.sessions: dict[Type[BakalariSession], list[BakalariSession]] = {}
        atexit.register(self.kill_all, False)

    def create_session(self, session_class: Type[Session], set_busy = True) -> Session:
        """Vytvoří novou session daného typu a navrátí ji.

        Pozn.:
            Nová session bude přidána do správy tohoto SessionManageru.

        Argumenty:
            session_class:
                Typ nové session.
            set_busy:
                Měla by být nová session označena jako "busy"? (Default: True)
        """
        session = session_class(self.bakalariAPI, set_busy)
        self.register_session(session)
        return session
    def get_session(self, session_class: Type[Session], set_busy = True, filter_busy = True) -> Session | None:
        """Navrátí (volnou) session daného typu. Pokud taková neexistuje, vrátí None.

        Argumenty:
            session_class:
                Typ session, která se má vyhledat.
            set_busy:
                Měla by být vrácená session označena jako "busy"? (Default: True)
            filter_busy:
                Ignorovat zaneprázdněné sessiony při hledání? (Default: True)
        """
        self.__lock.acquire()
        try:
            if session_class not in self.sessions:
                return None
            for session in self.sessions[session_class]:
                if not (filter_busy and session.busy):
                    session.busy = set_busy
                    return session #type: ignore - Pylance nechápe, že bound=BakalariSession znamená, že to vlastně je BakalariSession eShrug
        finally:
            self.__lock.release()
        return None
    def get_session_or_create(self, session_class: Type[Session], set_busy = True, filter_busy = True) -> Session:
        """Navrátí (volnou) session daného typu. Pokud taková neexistuje, vrátí None.

        Argumenty:
            session_class:
                Typ session, která se má vyhledat/vytvořit.
            set_busy:
                Měla by být vrácená session označena jako "busy"? (Default: True)
            filter_busy:
                Ignorovat zaneprázdněné sessiony při hledání? (Default: True)
        """
        session = self.get_session(session_class, set_busy, filter_busy)
        return self.create_session(session_class, set_busy) if session is None else session

    def register_session(self, session: BakalariSession):
        """Přidá danou session do správy SessionManageru.

        Pozn.:
            Jedna session může být pod správou více SessionManagerů.
            Samotné sessiony neví, pod správou jakého SessionManageru jsou (jestli nějakého).
            Pokud session potřebuje SessionManager, tak by si ho měla vzít přes referenci k BakalariAPI.

        Argumenty:
            session:
                Session, která se přidá do správy SessionManageru.
        """
        self.sessions.setdefault(type(session), []).append(session)
    def unregister_session(self, session: BakalariSession) -> bool:
        """Odebere danou session ze správy SessionManageru.

        Argumenty:
            session:
                Session, která se odebere ze správy SessionManageru.
        """
        if type(session) in self.sessions:
            try:
                self.sessions[type(session)].remove(session)
            except ValueError:
                return False
            return True
        return False

    def kill_all(self, nice: bool = True, session_class: Type[Session] | None = None):
        """Ukončí všechny sessiony.

        Argumenty:
            nice:
                Měly by se ukončit "mírumilovně"? (Default: True)
                (Pro význam slova "mírumilovně" viz BakalariSession.kill())
            session_class:
                Typ sessionů, které se mají ukončit; Pokud je None, ukončí se všechny. (Default: None)
        """
        self.__lock.acquire()
        try:
            if session_class is None:
                for sessions in self.sessions.values():
                    for session in sessions:
                        session.kill(nice)
                self.sessions = {}
            else:
                for session in self.sessions[session_class]:
                    session.kill(nice)
                del self.sessions[session_class]
        finally:
            self.__lock.release()
    def kill_dead(self, session_class: Type[Session] | None = None):
        """Ukončí všechny sessiony, které jsou již odhlášeni z Bakalářů.

        Argumenty:
            session_class:
                Typ sessionů, které se mají ukončit; Pokud je None, ukončí se všechny. (Default: None)
        """
        self.__lock.acquire()
        try:
            if session_class is None:
                for sessions in self.sessions.values():
                    for session in sessions:
                        if not session.is_logged():
                            session.kill(False)
                            self.unregister_session(session)
            else:
                for session in self.sessions[session_class]:
                    if not session.is_logged():
                        session.kill(False)
                        self.unregister_session(session)
        finally:
            self.__lock.release()

class BakalariAPI:
    """Hlavní třída BakalářiAPI. Pro normální použití stačí pouze tato classa.

    Attributes:
        username:
            Jméno pro přihlášení do Bakalářů.
        password:
            Heslo pro přihlášení do Bakalářů.
        selenium_handler:
            Instance classy SeleniumHandler obsahující nastavení Selenia.
        session_manager:
            Instance classy SessionMannager spravující sessiony.
        looting:
            Instance classy Looting spravující nálezy.
        user_info:
            Instance classy UserInfo obsahující údaje o uživaleli.
        server_info:
            Instance classy ServerInfo obsahující údaje o serveru a Bakalářích.
    """

    __parsers: dict[str, dict[Any, list[Callable[[GetterOutput], ResultSet]]]] = {x:{} for x in Endpoint._ENDPOINT_DICT.values()} # pylint: disable=protected-access
    # Hele... Tyhle věci mají name mangling, takže by na to nikdo neměl vůbec šahat, pokud neví, co to dělá (takže bych na to něměl šahat ani já KEKW)
    __resolvers: dict[Type[BakalariObject], list[Callable[[BakalariAPI, UnresolvedID], BakalariObject | None]]] = {}

    def __init__(self, url: str, username: str = "", password: str = "", seleniumHandler: SeleniumHandler | None = None):
        self.username: str = username
        self.password: str = password
        self.selenium_handler: SeleniumHandler | None = seleniumHandler
        self.session_manager: SessionManager = SessionManager(self)
        self.looting: looting.Looting = looting.Looting()
        self.user_info: UserInfo = UserInfo()
        self.server_info: ServerInfo = ServerInfo(url)
    def get_endpoint(self, endpoint: str) -> str:
        """Vrátí celou URL adresu daného endpointu.

        Vrácenou URL generuje přidáním URL aplikace/serveru Bakalářů před adresu endpointu.

        Args:
            endpoint:
                Adresa endpoinut.
                Měla by být vždy získána přes Endpoint třídu, tedy Endpoint.NEJAKY_ENDPOINT.

        Returns:
            Celou URL endpointu.
        """
        return self.server_info.url + endpoint
    def kill(self, nice: bool = True):
        """Ukončí všechny sessiony.

        Stejné jako volání 'session_manager.kill_all()'.

        Argumenty:
            nice:
                Měly by se ukončit "mírumilovně"? (Default: True)
                ((Pro význam slova "mírumilovně" viz BakalariSession.kill()))
        """
        self.session_manager.kill_all(nice)


    def get_fresh_grades(self, from_date: datetime | None = None) -> list[Grade]:
        """Nově načte a vrátí známky.

        Args:
            from_date:
                Pokud není None, načtou se známky pouze od daného data (včetně).
                Pokud je None, načtou se známky pouze ze současného pololetí.

        Returns:
            Nově načtený list známek.
        """
        return self._parse(modules.grades.getter(self, from_date)).retrieve_type(Grade)
    def get_fresh_all_grades(self) -> list[Grade]:
        """Nově načte a vrátí všechny známky.

        Returns:
            Nově načtený list všech známek.
        """
        return self.get_fresh_grades(from_date=datetime(1, 1, 1))

    def get_fresh_homeworks_fast(self) -> list[Homework]:
        """Nově načte a vrátí úkoly.

        Tato metoda vykoná načtení "rychle" (jelikož nevyužije Selenia), avšak zvládne načíst pouze prvních 20 aktivních nehotových úkolů.

        Returns:
            Nově načtený list úkolů.
        """
        return self._parse(modules.homeworks.getter_fast(self)).retrieve_type(Homework)
    def get_fresh_homeworks_slow(self, unfinished_only: bool = True, only_first_page: bool = False, first_loading_timeout: float = 5, second_loading_timeout: float = 10) -> list[Homework]:
        """Nově načte a vrátí úkoly.

        Tato metoda je pomalá. Pokud omezení metody `.get_fresh_homeworks_fast()` nejsou pro danou situaci omezující, zvažte její použití.

        Args:
            unfinished_only:
                Pokud je True, načte pouze úkoly označené jako nehotové.
                Pokud je False, načte hotové i nehotové úkoly.
            only_first_page:
                Pokud je True, načte úkoly jen z první stránky na Bakalářích.
                Pokud je False, načte úkoly ze všech stránek.
                Při užití metody je dobré zvážit, že načítání jednotlivých stránek úkolů je poměrně zdlouhavé.
            first_loading_timeout:
                Pro normální použití je vhodné nechat tak jak je.
                Určuje počet sekund, během kterých se vyčkává na zahájení načítání stránky.
                Pokud je číslo malé, je možné, že se nenačtou všechny úkoly.
                Pokud je číslo příliš velké, je možné, že zde bude v určitých případech veliká ztráta času.
            second_loading_timeout:
                Pro normální použití je vhodné nechat tak jak je.
                Určuje počet sekund, během kterých se vyčkává na skončení načítání stránky.
                Pokud je číslo malé, je možné, že BakalářiAPI usoudí, že v Bakalářích došlo k chybě a nenačte všechny úkoly.
                Pokud je číslo příliš velké, je možné, že zde bude v určitých případech veliká ztráta času.

        Returns:
            Nově načtený list úkolů.
        """
        output = modules.homeworks.get_slow(self, unfinished_only, only_first_page, first_loading_timeout, second_loading_timeout)
        self.looting.add_result_set(output)
        return output.retrieve_type(Homework)
    def get_fresh_all_homeworks(self) -> list[Homework]:
        """Nově načte a vrátí všechny úkoly.

        Tato metoda je pomalá. Pokud omezení metody `.get_fresh_homeworks_fast()` nejsou pro danou situaci omezující, zvažte její použití.

        Returns:
            Nově načtený list všech úkolů.
        """
        return self.get_fresh_homeworks_slow(unfinished_only=False, only_first_page=False)

    def get_fresh_meetings_future(self) -> list[Meeting]:
        """Nově načte a vrátí nadcházející schůzky.

        Returns:
            Nově načtený list nadcházejících schůzek.
        """
        return self._resolve(self._parse(modules.meetings.getter_future_meetings_ids(self)).retrieve_type(UnresolvedID)).retrieve_type(Meeting)
    def get_fresh_meetings(self, from_date: datetime, to_date: datetime) -> list[Meeting]:
        """Nově načte a vrátí schůzky.

        Je nutné specifikovat horní i dolní časovou hranici. Nejmenší možný čas je `datetime(1, 1, 1)`, největší možný je `datetime(9999, 12, 31, 23, 59, 59)`.

        Args:
            from_date:
                Určuje datum a čas, od kterého se mají schůzky načíst.
            to_date:
                Určuje datum a čas, do kterého se mají schůzky načíst.

        Returns:
            Nově načtený list schůzek.
        """
        return self._resolve(self._parse(modules.meetings.getter_meetings_ids(self, from_date, to_date))).retrieve_type(Meeting)
    def get_fresh_all_meetings(self) -> list[Meeting]:
        """Nově načte a vrátí všechny schůzky.

        Returns:
            Nově načtený list všech schůzek.
        """
        return self.get_fresh_meetings(datetime(1, 1, 1), datetime(9999, 12, 31, 23, 59, 59))

    def get_fresh_students(self) -> list[Student]:
        """Nově načte a vrátí seznam studentů.

        Returns:
            Nově načtený list studentů.
        """
        return self._parse(modules.meetings.getter_future_meetings_ids(self)).retrieve_type(Student)

    def get_fresh_komens(self, from_date: datetime | None = None, to_date: datetime | None = None, limit: int | None = None) -> list[Komens]:
        """Nově načte a vrátí komens zprávy.

        Kvůli limitaci Bakalářů je možné načíst pouze 300 zpráv na jednou.

        Args:
            from_date:
                Pokud není None, načtou se komens zprávy pouze od daného data.
                Pokue není None a parametr `to_date` je None, načtou se komens zprávy od daného data do současnosti.
                Pokud oba parametry `from_date` a `to_date` jsou None, načtou se komens zprávy pouze za poslední měsíc.
            to_date:
                Pokud není None, načtou se komens zprávy pouze do daného data.
                Pokue není None a parametr `from_date` je None, načtou se všechny komens zprávy do daného data.
                Pokud oba parametry `from_date` a `to_date` jsou None, načtou se komens zprávy pouze za poslední měsíc.
            limit:
                Určuje limit, kolik zpráv se maximálně načte.
                Při užití metody je dobré zvážit, že načítání jednotlivých zpráv je poměrně zdlouhavé.


        Returns:
            Nově načtený list komens zpráv.
        """
        return self._resolve(self._parse(modules.komens.getter_komens_ids(self, from_date, to_date)).retrieve_type(UnresolvedID)[:limit]).retrieve_type(Komens)
    def get_fresh_all_komens(self) -> list[Komens]:
        """Nově načte a vrátí všechny komens zprávy.

        Kvůli limitaci Bakalářů je možné načíst pouze 300 zpráv na jednou.

        Returns:
            Nově načtený list všech komens zpráv.
        """
        return self.get_fresh_komens(datetime(1953, 1, 1), datetime.today() + timedelta(1))

    def is_server_running(self) -> bool:
        """Zjistí, zda server/aplikace Bakalářů běží.

        Returns:
            True pokud server/aplikace běží, False pokud neběží.
        """
        try:
            response = requests.get(self.server_info.url)
            response.raise_for_status()
        except requests.exceptions.RequestException:
            return False
        return True
    def is_login_valid(self) -> bool:
        """Zjistí, zda jsou přihlašovací údaje správné.

        Returns:
            True pokud jsou přihlašovací údaje správné, False pokud nejsou.
        """
        session = self.session_manager.get_session_or_create(RequestsSession)
        output = session.login()
        if not output:
            session.kill()
            self.session_manager.unregister_session(session)
        else:
            session.busy = False
        return output
    def init(self):
        """Získá některé informace o systému Bakaláři a uživatelovi.

        Volání této metody není nutné, avšak zatím není jiný způsob (resp. není implementován), jak tyto informace získat.
        """
        session = self.session_manager.get_session_or_create(RequestsSession)
        data = json.loads(BeautifulSoup(session.get(self.get_endpoint(Endpoint.USER_INFO)).content, "html.parser").head["data-pageinfo"])
        self.user_info.type = data["userType"]
        self.user_info.hash = data["userHash"]
        self.server_info.version = data["applicationVersion"]
        self.server_info.version_date = datetime.strptime(data["appVersion"], "%Y%m%d")
        self.server_info.evid_number = int(data["evidNumber"])
        session.busy = False
    # def get_my_ID(self) -> str:
    #     #TODO: This
    #     #bakalariAPI.UserInfo.ID = ...
    #     return ""

    @classmethod
    def register_parser(cls, endpoint: str, type_: Type[GetterOutputTypeVar]):
        """Dekorátor, který zaregistruje funkci jako parser pro daný endpoint.

        Pro běžné užití BakalářiAPI není doporučeno tento dekorátor používat.
        Samotný dekorátor funkci nijak neupravuje.
        Dekorovaná funkce by měla brát GetterOutput (typu, který se passuje jako argument `type_` tohoto dekorátoru) a měla by vracet ResultSet či None, pokud není schopná z daného GetterOutput(u) nic získat.

        Args:
            endpoint:
                Endpoint, který daná funkce umí parsovat.
            type_:
                Typ generické třídy GetterOutput, který funkce přijímá.
        """
        # print(f"Endpoint:\t{endpoint}\nType:\t\t{type_}\nTypeVar:\t{GetterOutputTypeVar}\n")
        def decorator(func: Callable[[GetterOutput[GetterOutputTypeVar]], ResultSet]):
            cls.__parsers[endpoint].setdefault(type_, []).append(func)
            return func
        return decorator
    @classmethod
    def register_resolver(cls, type_: Type[BakalariObj]):
        """Dekorátor, který zaregistruje funkci jako resolver pro daný typ.

        Pro běžné užití BakalářiAPI není doporučeno tento dekorátor používat.
        Samotný dekorátor funkci nijak neupravuje.
        Dekorovaná funkce by měla brát UnresolvedID a měla by vracet typ, který se passuje v argumentu `type_` tohoto dekorátoru nebo None, pokud funkce není schopná resolvovat dané UnresovedID.

        Args:
            type_:
                Typ/Třída, pro kterou je tato funkce resolverem.
        """
        def decorator(func: Callable[[BakalariAPI, UnresolvedID[BakalariObj]], BakalariObj]):
            cls.__resolvers.setdefault(type_, []).append(func)
            return func
        return decorator

    def _parse(self, getter_output: GetterOutput[GetterOutputTypeVar]) -> ResultSet:
        """Extrahují se data z GetterOutput insance za pomoci registrovaných parserů.

        Pro běžné užití BakalářiAPI není doporučeno tuto funkci používat.
        Data získaná skrze tuto metodu jsou automaticky ukládána v looting instanci.

        Args:
            getter_output:
                GetterOutput, ze kterého se mají data extrahovat.

        Returns:
            ResultSet, který obsahuje všechna data od jednotlivých parserů.
        """
        output = ResultSet()
        for parser in self.__parsers[getter_output.endpoint].setdefault(getter_output.type, []): #TODO: Můžeme to prosím incializovat někde na začátku, ať nemusíme volat setdefault?
            parser_output = parser(getter_output)
            if parser_output is not None:
                output.merge(parser_output)
        self.looting.add_result_set(output)
        return output
    def _resolve(self, unresolved: UnresolvedID | list[UnresolvedID] | ResultSet) -> ResultSet:
        """Pokusí se získat plnohodnotný objekt pro dané UnresolvedID za pomoci registrovaných resolverů.

        Pro běžné užití BakalářiAPI není doporučeno tuto funkci používat.
        Data získaná skrze tuto metodu jsou automaticky ukládána v looting instanci.

        Args:
            unresolved:
                Jedno nebo více UnresolvedID, pro které se BakalářiAPI pokusí získat plnohodnotný objekt.

        Returns:
            ResultSet, který obsahuje všechna data od jednotlivých resolverů.
        """
        if isinstance(unresolved, ResultSet):
            output = unresolved
            unresolved = output.retrieve_type(UnresolvedID)
            output.remove(UnresolvedID)
        else:
            output = ResultSet()
            if not isinstance(unresolved, list):
                unresolved = [unresolved]

        for o in unresolved:
            if o.type in self.__resolvers:
                resolved = False
                for resolver in self.__resolvers[o.type]:
                    tmp = resolver(self, o)
                    if tmp is not None:
                        output.add_loot(tmp)
                        resolved = True
                        break
                if not resolved:
                    output.add_loot(o)
            else:
                output.add_loot(o)
        self.looting.add_result_set(output)
        return output

from . import exceptions, modules, looting
from .bakalariobjects import *
