from __future__ import annotations

import atexit
import json
from abc import ABC, abstractmethod
from threading import Lock, Thread
from typing import Type, TypeVar, cast, NoReturn
from time import sleep

import requests
from selenium.webdriver.remote.webdriver import WebDriver

from . import utils
from .bakalari import BakalariAPI, Endpoint


class BakalariSession(ABC):
    """Základní (abstraktní) classa pro typy sessionů.

    Definuje základní metody, které musí každý typ mít/implementovat.

    Atributy:
        bakalariAPI:
            Reference k přidružené BakalariAPI instanci, tedy instanci, pro kterou je tato session validní.
        busy:
            Je session zaneprázdněná?
    """

    def __init__(
        self, bakalariAPI: BakalariAPI, setBusy: bool = True, login: bool = True
    ):
        self.bakalariAPI: BakalariAPI = bakalariAPI
        self.busy: bool = setBusy
        self._auto_extend: bool = False
        if login:
            self.login()

    @abstractmethod
    def get_session_info(self) -> dict:
        """Získá a vrátí informace o současném sessionu.
        
        Returns:
            Parsovaná JSON data (viz dokumentace o enpointu "session_info").
        """

    def get_remaining(self) -> int:
        """Získá a vrátí zbývající životnost sessionu.
        
        Returns:
            Zbývající životnost sessionu.
        """
        return int(float(self.get_session_info()["remainingTime"]))
        # Taková cesta, jak převést string float na int :)

    @abstractmethod
    def login(self) -> bool:
        """Zkusí se přihlásit a vrátí výsledek.

        Returns:
            Pokud se úspěšně přihlásí, vrátí `True`, jinak `False`.
        """

    def is_logged(self) -> bool:
        # Implementace v závislosti na typu sessionu bude pravděpodobně rychlejší
        return self.get_remaining() != 0

    @abstractmethod
    def extend(self):
        """Prodlouží životnost sessionu."""

    @abstractmethod
    def kill(self, nice=True):
        """Ukončí session.
        
        Args:
            nice:
                Určuje, zda se session má z Bakalářů odhlásit.
                Pokud `True`, session se před ukončením řádně ohlásí z Bakalářů.
                Pokud `False`, session se ukončí bez odhlašování.
        """
        self.stop_extend_loop()

    def extend_loop(self, interval: float = 60):
        """Začne smyčku, ve které periodicky obnovuje životnost sessionu.

        Životnost sessionu se obnoví hned po spuštění metody.

        Args:
            internval:
                Interval obnovení sesisonu v sekundách.
        
        """
        self._auto_extend = True
        while self._auto_extend:
            self.extend()
            sleep(interval)
    def stop_extend_loop(self):
        """Ukončí smyčku na obnovování životnosti sessionu.
        
        Smyčce může trvat jeden cyklus (resp. dobu intervalu) než se ukončí.
        """
        self._auto_extend = False
            


class RequestsSession(BakalariSession):
    def __init__(
        self, bakalariAPI: BakalariAPI, setBusy: bool = True, login: bool = True
    ):
        self.session = requests.session()
        super().__init__(bakalariAPI, setBusy, login)

    def extend(self):
        self.busy = True
        self.session.get(self.bakalariAPI.get_endpoint(Endpoint.SESSION_EXTEND))
        self.busy = False

    def kill(self, nice=True):
        if nice:
            self.session.get(self.bakalariAPI.get_endpoint(Endpoint.LOGOUT))
        self.session.close()
        super().kill(nice)

    def get_session_info(self) -> dict:
        self.busy = True
        output = self.session.get(
            self.bakalariAPI.get_endpoint(Endpoint.SESSION_INFO)
        ).json()
        self.busy = False
        return output

    def login(self) -> bool:
        self.busy = True
        output = self.session.post(
            self.bakalariAPI.get_endpoint(Endpoint.LOGIN),
            {
                "username": self.bakalariAPI.username,
                "password": self.bakalariAPI.password,
            },
            allow_redirects=False
        ).is_redirect
        self.busy = False
        return output

    def is_logged(self) -> bool:
        self.busy = True
        response = self.session.get(self.bakalariAPI.get_endpoint(Endpoint.DASHBOARD), allow_redirects=False)
        self.busy = False
        return not response.is_redirect

    def get(self, *args, **kwargs) -> requests.Response:
        return self.session.get(*args, **kwargs)

    def post(self, *args, **kwargs) -> requests.Response:
        return self.session.post(*args, **kwargs)


class SeleniumSession(BakalariSession):
    def __init__(
        self,
        bakalariAPI: BakalariAPI,
        setBusy: bool = True,
        login: bool = True,
        enable_requests_acceleration: bool = True,
    ):
        self.session: WebDriver = bakalariAPI.selenium_handler.open()
        self.requests_acceleration: bool = enable_requests_acceleration
        super().__init__(bakalariAPI, setBusy, login)

    def get_session_info(self) -> dict:
        if self.requests_acceleration:
            return requests.get(
                self.bakalariAPI.get_endpoint(Endpoint.SESSION_INFO),
                cookies=utils.cookies_webdriver2requests(self.session),
            ).json()
        else:
            self.busy = True
            self.session.get(self.bakalariAPI.get_endpoint(Endpoint.SESSION_INFO))
            output = json.loads(self.session.page_source)
            self.busy = False
            return output

    def extend(self):
        if self.requests_acceleration:
            requests.get(
                self.bakalariAPI.get_endpoint(Endpoint.SESSION_EXTEND),
                cookies=utils.cookies_webdriver2requests(self.session),
            )
        else:
            self.busy = True
            self.session.get(self.bakalariAPI.get_endpoint(Endpoint.SESSION_EXTEND))
            self.busy = False

    def kill(self, nice=True):
        # try:
        if nice:
            self.session.get(self.bakalariAPI.get_endpoint(Endpoint.LOGOUT))
        self.session.close()
        # except WebDriverException: # Kvůli tomu, když nějakým záhadným způsobem je už webdriver mrtvý (resp. zavřený) :)
        #     #No... Dost nepěkné řešení, jelikož tohle chytí úplně všecho, co se pokazí, ale lepší řešení neexistuje eShrug
        #     pass
        super().kill(nice)

    def login(self) -> bool:
        if self.requests_acceleration:
            output = requests.post(
                self.bakalariAPI.get_endpoint(Endpoint.LOGIN),
                {
                    "username": self.bakalariAPI.username,
                    "password": self.bakalariAPI.password,
                },
                allow_redirects=False
            )
            if output.is_redirect:
                self.busy = True
                cookies = utils.cookies_requests2webdriver(output.cookies)

                # Musíme být na správné stránce, jelikož jinak se nám vrátí error o špatné doméně,
                # kterou si to případně domyslí, když je na dané stránce I guess a asi není nejlepší
                # řešení dávat doménu "na tvrdo" (domain = bakalariAPI.url), takže to je (zatím) takto
                self.session.get(self.bakalariAPI.get_endpoint(Endpoint.LOGIN))
                for cookie in cookies:
                    self.session.add_cookie(cookie)
                self.busy = False
                return True
            else:
                return False
        else:
            self.busy = True
            self.session.get(self.bakalariAPI.get_endpoint(Endpoint.LOGIN))
            self.session.find_element_by_id("username").send_keys(self.bakalariAPI.username)
            self.session.find_element_by_id("password").send_keys(self.bakalariAPI.password)
            self.session.find_element_by_id("loginButton").click()
            output = self.session.current_url != self.bakalariAPI.get_endpoint(Endpoint.LOGIN)
            self.busy = False
            return output

    def is_logged(self) -> bool:
        if self.requests_acceleration:
            response = requests.get(
                self.bakalariAPI.get_endpoint(Endpoint.DASHBOARD),
                cookies=utils.cookies_webdriver2requests(self.session),
                allow_redirects=False
            )
            return not response.is_redirect
        else:
            self.busy = True
            self.session.get(self.bakalariAPI.get_endpoint(Endpoint.DASHBOARD))
            output = self.session.current_url == self.bakalariAPI.get_endpoint(Endpoint.DASHBOARD)
            self.busy = False
            return output


Session = TypeVar("Session", bound=BakalariSession)


class SessionManager:
    """Classa, která spravuje sessiony.

    Atributy:
        bakalariAPI:
            Reference k BakalářiAPI, pro které spravuje sessiony.
        sessions:
            Slovník, který obsahuje všechny sessiony pod správou tohoto SessionMannageru.
            Klič je typ sessionu jako string (tedy název classy sessionu) a hodnota je list sessionů tohoto typu.
        start_auto_extend:
            Pokud `True`, automaticky u sessionů zapne `auto_extend()` v nové deamon threadu.
            Pokud `False`, tak nic.
            Default je `False`, jelikož ve většině případů session přežije po potřebnou dobu i bez `extend()`
            a zbytečně se nevytvářejí theady.
    """

    def __init__(self, ref: BakalariAPI, start_auto_extend: bool = False):
        self.__lock = Lock()
        self.bakalariAPI: BakalariAPI = ref
        self.sessions: dict[Type[BakalariSession], list[BakalariSession]] = {}
        self.start_auto_extend: bool = start_auto_extend
        atexit.register(self.kill_all, False)

    def create_session(self, session_class: Type[Session], set_busy=True) -> Session:
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
        if self.start_auto_extend:
            Thread(target=session.extend_loop, daemon=True).start()
        return session

    def get_session(
        self, session_class: Type[Session], set_busy=True, filter_busy=True
    ) -> Session | None:
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
                    return cast(Session, session)
        finally:
            self.__lock.release()
        return None

    def get_session_or_create(
        self, session_class: Type[Session], set_busy=True, filter_busy=True
    ) -> Session:
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
        return (
            self.create_session(session_class, set_busy) if session is None else session
        )

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
