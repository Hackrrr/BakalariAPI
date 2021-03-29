"""Hlavní část BakalářiAPI.

Tento modul/script obsahuje většinu věcí z celého BakalářiAPI - Prakticky vše krom definice BakalariObject class a samotné implementace BakalářiAPI modulů.
"""


from __future__ import annotations

import atexit
import inspect
import json
import sys
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Type

import requests
from selenium import webdriver
from selenium.common.exceptions import WebDriverException

from . import utils

#TODO: logging module
#TODO: Get Komens/Homework/Metting/... with ID methods
#TODO: Projet všechny proměnné s časy a převést je na non-aware (= naive) datetime
# Zde bylo rozhodování mezi timestamp, naive datetime a aware datetime. Proč tedy vyhrál naive datetime? No...
# 1. timestamp < naive datetime         - Mělo by to být "ekvivaletní" (tzn. bez ztrát přesnosti), ale u datetimu máme navíc nějaký fancy funkce
# 2. aware datetime < naive datetime    - Nevím, jestli je vážně aware horší (nejspíše ne), ale nechci to do něj převádět, protože pásma OMEGALUL
#TODO: Přibyl klíč MeetingProviderId v detailech schůzky (od poslední verte (1.37.*)) + nové okénko v UI (kde se schůzka konná (př. MS Teams)); Hodnota je číslo => Někde je JS na konverzi čísla do "produktu" => seznam
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


LAST_SUPPORTED_VERSION = "1.37.208.1"



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
    def __init__(self, bakalariAPI: BakalariAPI, setBusy: bool = True, login: bool = True):
        self.session: webdriver = bakalariAPI.selenium_handler.open()
        super().__init__(bakalariAPI, setBusy)
        #TODO: We can probrally do something faster (like direct POST)
        
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

class SessionManager:
    """Classa, která spravuje sessiony.

    Atributy:
        bakalariAPI:
            Reference k BakalářiAPI, pro které spravuje sessiony.
        sessions:
            Slovník, který obsahuje všechny sessiony pod správou tohoto SessionMannageru.
            Klič je typ sessionu jako string (tedy název classy sessionu) a hodnota je list sessionů tohoto typu.
    """
    #TODO: Thread-safe session getter (because we really don't want to have "shared" session :) )
    def __init__(self, ref: BakalariAPI):
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
        if session_class not in self.sessions:
            return None
        for session in self.sessions[session_class]:
            if not (filter_busy and session.busy):
                session.busy = set_busy
                return session
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
        if session_class is None:
            for session_class in self.sessions:
                for session in self.sessions[session_class]:
                    session.kill(nice)
            self.sessions = {}
        else:
            for session in self.sessions[session_class]:
                session.kill(nice)
            del self.sessions[session_class]
    def kill_dead(self, session_class: Type[BakalariSession] = None):
        """Ukončí všechny sessiony, které jsou již odhlášeni z Bakalářů.

        Argumenty:
            session_class:
                Typ sessionů, které se mají ukončit; Pokud je None, ukončí se všechny. (Default: None)
        """
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

class BakalariAPI:
    """Hlavní classa BakalářiAPI. Pro normální použití stačí pouze tato classa.

    Atributy:
        url:
            HTTP adresa webového rozhraní Bakalářů.
            Musí být ve validním HTTP scématu, např. "https://bakalari.mojeskola.cz".
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
    def __init__(self, url: str, username: str = None, password: str = None, seleniumHandler: SeleniumHandler = None):
        self.url: str = url #TODO: Migrate this to ServerInfo
        self.username: str = username
        self.password: str = password
        self.selenium_handler: SeleniumHandler = seleniumHandler
        self.session_manager: SessionManager = SessionManager(self)
        self.looting: Looting = Looting()
        self.user_info: UserInfo = UserInfo()
        self.server_info: ServerInfo = ServerInfo()
    def get_endpoint(self, endpoint: str) -> str:
        """Vrátí celou URL adresu daného endpointu"""
        return self.url + endpoint
    def kill(self, nice: bool = True):
        """Ukončí všechny sessiony.

        Stejné jako volání 'session_manager.kill_all()'.

        Argumenty:
            nice:
                Měly by se ukončit "mírumilovně"? (Default: True)
                (Pro význam slova "mírumilovně" viz BakalariSession.kill())
        """
        self.session_manager.kill_all(nice)


    ### Generated by ModuleMethodsExtracter.py ###
    def get_grades(self, from_date: datetime = None) -> list[Grade]: pass
    def get_all_grades(self) -> list[Grade]: pass

    def get_homeworks_fast(self) -> list[str]: pass
    def get_homeworks(self, unfinished_only: bool = True, only_first_page: bool = False, first_loading_timeout: float = 5, second_loading_timeout: float = 10) -> list[Homework]: pass

    def get_komens_IDs(self, from_date: datetime = None, to_date: datetime = None) -> list[str]: pass
    def get_all_komens_IDs(self): pass
    def get_komens(self, ID: str, context: str = "prijate") -> Komens: pass

    def get_meeting(self, ID: str) -> Meeting: pass
    def get_future_meetings_IDs(self) -> list[str]: pass
    def get_meetings_IDs(self, from_date: datetime, to_date: datetime) -> list[str]: pass
    def get_all_meetings_IDs(self) -> list[str]: pass

    def is_server_running(self) -> bool: pass
    def is_login_valid(self) -> bool: pass
    def init(self): pass
    def get_my_ID(self) -> str: pass
    ### Generated by ModuleMethodsExtracter.py ###


from .bakalariobjects import *


class Looting:
    class JSONSerializer(json.JSONEncoder):
        def default(self, o):
            if isinstance(o, datetime):
                return {
                    "_type":   "datetime",
                    "value":    str(o)
                }
            if isinstance(o, BakalariObject):
                output = dict(o.__dict__)
                output["_type"] = type(o).__name__
                if "Instance" in output:
                    del output["Instance"]
                return output
            #raise TypeError()

    def __init__(self):
        self.Data: dict[str, BakalariObject] = {}
        self.IDs: dict[str, BakalariObject] = {}

    def add_loot(self, object: BakalariObject, skipCheck: bool = False) -> bool:
        """Adds object to loot if it's ID is not already there; Returns True when object is added, False otherwise"""

        if not skipCheck and object.ID in self.IDs:
            return False
        self.Data.setdefault(type(object).__name__, []).append(object)
        self.IDs[object.ID] = object
        return True
    def add_loot_array(self, lootArray: list[BakalariObject]):
        for loot in lootArray:
            self.add_loot(loot)

    def export_JSON(self, byIDs: bool = False, ensure_ascii: bool = False):
        return self.JSONSerializer(ensure_ascii = ensure_ascii).encode(self.IDs if byIDs else self.Data)

    def import_JSON(self, jsonString: str, skipCheck: bool = False):
        parsed = json.loads(jsonString)
        module = __import__(__name__)

        def Recursion(data) -> object:
            for index, value in (enumerate(data) if isinstance(data, list) else data.items()):
                #print(f"Enumerating index '{index}', value: {value}")
                if isinstance(value, list) or isinstance(value, dict):
                    data[index] = Recursion(value)
            if isinstance(data, dict) and "_type" in data:
                if data["_type"] == "datetime":
                    data = utils.string2datetime(data["value"])
                else:
                    if not hasattr(module, data["_type"]):
                        raise TypeError("Unknown type to load; Type: " + data["_type"])
                    class_constructor = getattr(module, data["_type"])
                    signature = inspect.signature(class_constructor)
                    supply_list = []
                    for param in signature.parameters:
                        param = param.lstrip("_")
                        # print(f"Trying to add '{param}'...")
                        if param in data:
                            supply_list.append(data[param])
                            # print(f"Added '{param}' with value '{data[param]}'")
                    # print(f"In signature: {len(signature.parameters)}; In supply_list: {len(supply_list)}")
                    data = class_constructor(*supply_list)
                    #print("Adding new object to Loot (" + class_constructor.__name__ + ")")
                    self.add_loot(data, skipCheck)
            return data
        
        parsed = Recursion(parsed)

    #TODO: Merge loots



def bakalarilootable(func):
    def wrapper(*args, **kwargs):
        # First argument MUST BE BakalariAPI ref!
        # => args[0] == BakalariAPI
        output = func(*args, **kwargs)
        if isinstance(output, BakalariObject):
            args[0].looting.add_loot(output)
        else:
            args[0].looting.add_loot_array(output)
        return output
    return wrapper
def bakalariextension(extension):
    setattr(BakalariAPI, extension.__name__, extension)
    return extension
def bakalarilootable_extension(extension):
    # Ok, tohle je takový zvláštní... Jelikož passujeme výsledek z 'bakalariLootable' přímo do 'bakalariExtension', tak vzniká problém,
    # protože z 'bakalariLootable' se nám vrací wrapper funkce - a jelikož se 'bakalariExtension' řídí podle '__name__', tak se vytvoří
    # atribut "wrapper". Naštěstí Python dovoluje přepsat '__name__', takže ho může "opravit"...
    originalName = extension.__name__
    lootable = bakalarilootable(extension)
    lootable.__name__ = originalName
    return bakalariextension(lootable)
