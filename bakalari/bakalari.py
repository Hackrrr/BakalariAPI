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
import inspect
import json
import sys
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from enum import Enum
from multiprocessing import Lock
from typing import Type, Union

import requests
from bs4 import BeautifulSoup

_HAVE_SELENIUM = False
try:
    from selenium import webdriver
    _HAVE_SELENIUM = True
except ImportError:
    pass

#TODO: logging module
#TODO: Projet všechny proměnné s časy a převést je na non-aware (= naive) datetime
# Zde bylo rozhodování mezi timestamp, naive datetime a aware datetime. Proč tedy vyhrál naive datetime? No...
# 1. timestamp < naive datetime         - Mělo by to být "ekvivaletní" (tzn. bez ztrát přesnosti), ale u datetimu máme navíc nějaký fancy funkce
# 2. aware datetime < naive datetime    - Nevím, jestli je vážně aware horší (nejspíše ne), ale nechci to do něj převádět, protože pásma OMEGALUL
#TODO: Přibyl klíč MeetingProviderId v detailech schůzky (od poslední verze (1.37.*)) + nové okénko v UI (kde se schůzka konná (př. MS Teams)); Hodnota je číslo => Někde je JS na konverzi čísla do "produktu" => seznam
# Nalezeno - Přidal se script tag před script tag, který hledáme kvůli studentům - Definuje objekt 'Dictionaries', kde je klíč 'MeetingProvider', kde je array, jejíž indexy se shodují s ID "providera" - Máme tu Google Meet, MS Teams a None :)
# Řádek 103 - 111 (v MeetingsOverview (normální stránka))
#TODO: Vytvoření parametrického session dekorátor, který by řešil sessiony:
# Nice to have featura by totiž byla taková, že bych mohl přes argument funkce v (bakalariAPI) modulu určit session, která by se použila
# K tomu by mohl sloužit parametrický dekorátor, který by vzal jako parametr session classu a obalil by funkci:
#   1. Ověřením, zda se passuje nějaká session - Jestli ano, nic se neděje. Jesli ne, vytvoří se (resp. vyžádá se jedna od session manageru) a passuje se ta
#   2. Nastavením "busy" na sessionu (pokud už není)
#   3. Odnastavením "busy" na sessionu
# Nutno podotknout, že by se muselo více domyslet (od)nastavení "busy" atributu. Pravděpodobně nějak takto:
#   Session je dána:
#       Pokud je nastaveno "busy", nech "busy" i po skončení
#       Pokud není, nastav a následně odnastav
#   Session se musí vyžádat od session manageru:
#       Vyžádá se session s "setBusy = True" a po skončení se odnastavý

LAST_SUPPORTED_VERSION = "1.37.208.1"

class Browser(Enum):
    """Enum prohlížečů/browserů podporovaných Seleniem"""
    CHROME = 0
    FIREFOX = 1
    EDGE = 2
    SAFARI = 3
    OPERA = 4
    IE = 5
class SeleniumHandler:
    """    Třída obsahujcí nastavení pro Selenium.
    """
    def __init__(self, browser: Browser, executable_path: str = "", params: dict = {}):
        if "selenium" not in sys.modules:
            raise ImportError(name="selenium")
        self.browser: Browser = browser
        self.executable_path: str = executable_path
        self.params: dict = params
    def open(self, try_silent: bool = True) -> webdriver:
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
    def __init__(self, loot: Union[BakalariObject, list[BakalariObject]] = None):
        self.data: dict[str, list[BakalariObject]] = {}
        if loot is not None:
            self.add_loot(loot)
    def add_loot(self, loot: Union[BakalariObject, list[BakalariObject]]) -> ResultSet:
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
    def retrieve_type(self, _type: Type[BakalariObject]) -> list[BakalariObject]:
        t = _type.__name__
        return self.data[t] if t in self.data else []
    def merge(self, result_set: ResultSet):
        for (t, lst) in result_set.data.items():
            self.data[t] = self.data.setdefault(t, []) + lst
    def remove(self, _type: Type[BakalariObject]):
        try:
            del self.data[_type]
        except KeyError:
            pass
class GetterOutput:
    class Types(Enum):
        SOUP = 0
        JSON = 1
    def __init__(self, type_: Types, endpoint: str, data):
        self.type: GetterOutput.Types = type_
        self.endpoint: str = endpoint
        #                    SOUP        JSON
        self.data: Union[BeautifulSoup, object] = data

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
    def get_session_info(self) -> object:
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
    def get_session_info(self) -> object:
        return self.session.get(self.bakalariAPI.get_endpoint(Endpoint.SESSION_INFO)).json()
    def login(self) -> bool:
        return self.session.post(self.bakalariAPI.get_endpoint(Endpoint.LOGIN), {
            "username": self.bakalariAPI.username,
            "password": self.bakalariAPI.password
        }).url != self.bakalariAPI.get_endpoint(Endpoint.LOGIN)
    def is_logged(self) -> bool:
        pass #TODO: This

    def get(self, *args, **kwargs) -> requests.Response:
        return self.session.get(*args, **kwargs)
    def post(self, *args, **kwargs) -> requests.Response:
        return self.session.post(*args, **kwargs)
class SeleniumSession(BakalariSession):
    #TODO: Zde mi přijde, že je možná hromada optimalizace - Webdriver můžeme nechat na pokoji a používat jen request modul,
    # abychom nemuseli čekat na webdriver. Teoreticky bychom mohli vytvořit interní RequestSession, kterému by byly přidány jen cookies
    # a přes něj by jsme mohli dělat "util" věci (extend, login, is_logged, ...)
    def __init__(self, bakalariAPI: BakalariAPI, setBusy: bool = True, login: bool = True):
        if not _HAVE_SELENIUM:
            raise Exception
        self.session: webdriver = bakalariAPI.selenium_handler.open()
        super().__init__(bakalariAPI, setBusy)
        
    def get_session_info(self) -> object:
        return json.loads(self.session.get(self.bakalariAPI.get_endpoint(Endpoint.SESSION_INFO)))
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
        pass #TODO: This
if not _HAVE_SELENIUM:
    class SeleniumSession(): # pylint: disable=function-redefined
        """'Falešná' SeleniumSession třída, která nahrazuje skutečnou v případě, že chybí Selenium"""
        def __init__(self):
            raise exceptions.NoSeleniumException()

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
        self.sessions: dict[str, list[BakalariSession]] = {}
        atexit.register(self.kill_all, False)

    def create_session(self, session_class: Type[BakalariSession], set_busy = True) -> BakalariSession:
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
    def get_session(self, session_class: Type[BakalariSession], set_busy = True, filter_busy = True) -> BakalariSession:
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
                    return session
        finally:
            self.__lock.release()
        return None
    def get_session_or_create(self, session_class: Type[BakalariSession], set_busy = True, filter_busy = True) -> BakalariSession:
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

    def kill_all(self, nice: bool = True, session_class: Type[BakalariSession] = None):
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
                for session_class in self.sessions:
                    for session in self.sessions[session_class]:
                        session.kill(nice)
                self.sessions = {}
            else:
                for session in self.sessions[session_class]:
                    session.kill(nice)
                del self.sessions[session_class]
        finally:
            self.__lock.release()
    def kill_dead(self, session_class: Type[BakalariSession] = None):
        """Ukončí všechny sessiony, které jsou již odhlášeni z Bakalářů.

        Argumenty:
            session_class:
                Typ sessionů, které se mají ukončit; Pokud je None, ukončí se všechny. (Default: None)
        """
        self.__lock.acquire()
        try:
            if session_class is None:
                for session_class in self.sessions:
                    for session in self.sessions[session_class]:
                        if not session.IsLogged():
                            session.kill(False)
                            self.unregister_session(session)
            else:
                for session in self.sessions[session_class]:
                    if not session.IsLogged():
                        session.kill(False)
                        self.unregister_session(session)
        finally:
            self.__lock.release()

class BakalariAPI:
    """Hlavní třída BakalářiAPI. Pro normální použití stačí pouze tato classa.

    Atributy:
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

    # __getters: dict = {x:[] for x in Endpoint._ENDPOINT_DICT.values()} # pylint: disable=protected-access
    __parsers: dict[str, list] = {x:[] for x in Endpoint._ENDPOINT_DICT.values()} # pylint: disable=protected-access
    # Budeme tiše mlčet o tom, že tu máme dva "typy" parserů (HTML(= BeautifulSoup) a JSON (= object)) (vlastně i getterů)
    # a předpokládat, že se trefíme vždy správně...
    # Hele... Tyhle věci mají name mangling, takže by na to nikdo neměl vůbec šahat, pokud neví, co to dělá LULW

    __resolvers: dict[type, list] = {}

    def __init__(self, url: str, username: str = None, password: str = None, seleniumHandler: SeleniumHandler = None):
        self.username: str = username
        self.password: str = password
        self.selenium_handler: SeleniumHandler = seleniumHandler
        self.session_manager: SessionManager = SessionManager(self)
        self.looting: Looting = Looting()
        self.user_info: UserInfo = UserInfo()
        self.server_info: ServerInfo = ServerInfo(url)
    def get_endpoint(self, endpoint: str) -> str:
        """Vrátí celou URL adresu daného endpointu"""
        return self.server_info.url + endpoint
    def kill(self, nice: bool = True):
        """Ukončí všechny sessiony.

        Stejné jako volání 'session_manager.kill_all()'.

        Argumenty:
            nice:
                Měly by se ukončit "mírumilovně"? (Default: True)
                (Pro význam slova "mírumilovně" viz BakalariSession.kill())
        """
        self.session_manager.kill_all(nice)


    def get_fresh_grades(self, from_date: datetime = None) -> list[Grade]:
        return self.__parse(modules.grades.getter(self, from_date)).retrieve_type(Grade)
    def get_fresh_all_grades(self) -> list[Grade]:
        return self.get_fresh_grades(from_date=datetime(1, 1, 1))

    def get_fresh_homeworks_fast(self) -> list[Homework]:
        return self.__parse(modules.homeworks.getter_fast(self)).retrieve_type(Homework)
    def get_fresh_homeworks_slow(self, unfinished_only: bool = True, only_first_page: bool = False, first_loading_timeout: float = 5, second_loading_timeout: float = 10) -> list[Homework]:
        output = modules.homeworks.get_slow(self, unfinished_only, only_first_page, first_loading_timeout, second_loading_timeout)
        self.looting.add_result_set(output)
        return output.retrieve_type(Homework)
    def get_fresh_all_homeworks(self) -> list[Homework]:
        return self.get_fresh_homeworks_slow(unfinished_only=False, only_first_page=False)

    def get_fresh_meetings_future(self) -> list[Meeting]:
        return self.__resolve(self.__parse(modules.meetings.getter_future_meetings_ids(self)).retrieve_type(UnresolvedID)).retrieve_type(Meeting)
    def get_fresh_meetings(self, from_date: datetime, to_date: datetime) -> list[Meeting]:
        return self.__resolve(self.__parse(modules.meetings.getter_meetings_ids(self, from_date, to_date))).retrieve_type(Meeting)
    def get_fresh_all_meetings(self) -> list[Meeting]:
        self.get_fresh_meetings(datetime(1, 1, 1), datetime(9999, 12, 31, 23, 59, 59))

    def get_fresh_students(self) -> list[Student]:
        return self.__parse(modules.meetings.getter_future_meetings_ids(self)).retrieve_type(Student)

    def get_fresh_komens(self, from_date: datetime = None, to_date: datetime = None) -> list[Komens]:
        return self.__resolve(self.__parse(modules.komens.getter_komens_ids(self, from_date, to_date))).retrieve_type(Komens)
    def get_fresh_all_komens(self) -> list[Komens]:
        return self.get_fresh_komens(datetime(1953, 1, 1), datetime.today() + timedelta(1))

    def is_server_running(self) -> bool:
        try:
            response = requests.get(self.server_info.url)
            response.raise_for_status()
        except requests.exceptions.RequestException:
            return False
        return True
    def is_login_valid(self) -> bool:
        session = self.session_manager.get_session_or_create(RequestsSession)
        output = session.login()
        if not output:
            session.kill()
            self.session_manager.unregister_session(session)
        else:
            session.busy = False
        return output
    def init(self):
        session = self.session_manager.get_session_or_create(RequestsSession)
        data = json.loads(BeautifulSoup(session.get(self.get_endpoint(Endpoint.USER_INFO)).content, "html.parser").head["data-pageinfo"])
        self.user_info.type = data["userType"]
        self.user_info.hash = data["userHash"]
        self.server_info.version = data["applicationVersion"]
        self.server_info.version_date = datetime.strptime(data["appVersion"], "%Y%m%d")
        self.server_info.evid_number = int(data["evidNumber"])
        session.busy = False
    def get_my_ID(self) -> str:
        #TODO: This
        #bakalariAPI.UserInfo.ID = ...
        pass

    @classmethod
    def register_parser(cls, endpoint: str):
        def decorator(func):
            cls.__parsers[endpoint].append(func)
            # def wrapper(*args, **kwargs) -> ResultSet:
            #     output = func(*args, **kwargs)
            #     return output
            # return wrapper
            return func
        return decorator
    @classmethod
    def register_resolver(cls, type_: Type[BakalariObject]):
        def decorator(func):
            cls.__resolvers.setdefault(type_, []).append(func)
            return func
        return decorator

    def __parse(self, getter_output: GetterOutput) -> ResultSet:
        output = ResultSet()
        for parser in self.__parsers[getter_output.endpoint]:
            parser_output = parser(getter_output)
            if parser_output is not None:
                output.merge(parser_output)
        self.looting.add_result_set(output)
        return output
    def __resolve(self, unresolved: Union[UnresolvedID, list[UnresolvedID], ResultSet]) -> ResultSet:
        if isinstance(unresolved, ResultSet):
            output = unresolved
            unresolved = unresolved.retrieve_type(UnresolvedID)
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
        return output

from .bakalariobjects import *
from . import exceptions, modules


class Looting:
    """Třída obsatarávající sesbírané objekty pro pozdější použití.

    Atributy:
        data:
            TODO: Doc
    """
    class JSONEncoder(json.JSONEncoder):
        def default(self, o):
            if isinstance(o, datetime):
                return {
                    #TODO: Format
                    "_type":    "datetime",
                    "value":    str(o)
                }
            if isinstance(o, BakalariObject):
                output = dict(o.__dict__)
                output["_type"] = type(o).__name__
                if "Instance" in output:
                    del output["Instance"]
                return output
            return super().default(o)
    class JSONDecoder(json.JSONDecoder):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, object_hook=self.hook, **kwargs)
        def hook(self, o):
            if "_type" not in o:
                return o
            if o["_type"] == "datetime":
                pass #TODO: datetime deserialization
            # elif o["_type"] == "":
            #     pass
            else:
                module = __import__(__name__)
                if not hasattr(module, o["_type"]):
                    raise TypeError("Unknown type to load; Type: " + o["_type"])
                
                #TODO: Wait... Mám takový nemilý pocit, že máme zranitelnost... OMEGALUL
                # Jelikož tento modul obsahuje "os" (skrze bakalariobject wildcard import), tak je možné, že pokud bude
                # hodnota "_type" nastavena na "os.system", tak .... jo. Problém... LULW (hodnoty z parsovaného objekt
                # totiž bereme jako "paramater name":"value" pár a ten pak vkládáme do konstruktoru)
                # Možný exploit tedy vypadá nějak takto: (ale jsem línej to testovat)
                # {"_type":"os.system", "command":"start calc.exe"}
                
                class_constructor = getattr(module, o["_type"])
                signature = inspect.signature(class_constructor)
                supply_list = []
                for param in signature.parameters:
                    param = param.lstrip("_") #TODO: Remove?
                    # print(f"Trying to add '{param}'...")
                    if param in o:
                        supply_list.append(o[param])
                        # print(f"Added '{param}' with value '{data[param]}'")
                # print(f"In signature: {len(signature.parameters)}; In supply_list: {len(supply_list)}")
                return class_constructor(*supply_list)
                #print("Adding new object to Loot (" + class_constructor.__name__ + ")")

    def __init__(self):
        self.__lock = Lock()
        self.data: dict[str, dict[str, BakalariObject]] = {}
        # Proč máme "root" key jako 'str' a ne jako 'type'? V runtimu asi lepší to mít jako 'type', ale při serializaci
        # nechci řešit nemožnost serializovat typ 'type' a při deserializaci nechci konvertovat něco (= typ, jako který
        # se to serializuje) zpátky na 'type'. Navíc I guess, že když __name__ je atribut, tak to prakticky nezabere nic.
        self.unresolved: list[UnresolvedID] = []
    
    def __add_one(self, o: BakalariObject):
        #TODO: Remove unresolved if resolved
        if isinstance(o, UnresolvedID):
            self.unresolved.append(o)
        else:
            self.data.setdefault(type(o).__name__, {})[o.ID] = o

    def add_loot(self, loot: Union[BakalariObject, list[BakalariObject]]):
        if not isinstance(loot, list):
            loot = [loot]
        self.__lock.acquire()
        try:
            for o in loot:
                self.__add_one(o)
        finally:
            self.__lock.release()
    def add_result_set(self, result_set: ResultSet):
        for lst in result_set.data.values():
            self.add_loot(lst)
            # Jsem myslel, že to bude o trochu víc komplexnejší (jako třeba přeskočení resolvování typů) ale dopadlo to takhle KEKW


    def export_JSON(self, *args, **kwargs):
        return json.dumps(self.data, cls=self.JSONEncoder, *args, **kwargs)

    def import_JSON(self, json_string: str, *args, **kwargs):
        self.data = json.loads(json_string, cls=self.JSONDecoder, *args, **kwargs)

    #TODO: Merge loots
