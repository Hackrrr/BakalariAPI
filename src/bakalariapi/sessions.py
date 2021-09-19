"""Modul obsahující věci ohledně sessionů."""

from __future__ import annotations

import atexit
import json
from abc import ABC, abstractmethod
from threading import Lock, Thread
from time import sleep
from typing import TypeVar, cast

import requests
from selenium.webdriver.remote.webdriver import WebDriver

from . import exceptions, utils
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
        """Zjistí, zda je session přihlášená.

        Returns:
            Pokud je session přihlášená, vrátí `True`, jinak `False`.
        """
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

    def __enter__(self: Session) -> Session:
        self.busy = True
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.busy = False


class RequestsSession(BakalariSession):
    """Session využívající `requests` modul."""

    def __init__(
        self, bakalariAPI: BakalariAPI, setBusy: bool = True, login: bool = True
    ):
        self.session = requests.session()
        super().__init__(bakalariAPI, setBusy, login)

    def extend(self):
        with self:
            self.session.get(self.bakalariAPI.get_endpoint(Endpoint.SESSION_EXTEND))

    def kill(self, nice=True):
        if nice:
            self.session.get(self.bakalariAPI.get_endpoint(Endpoint.LOGOUT))
        self.session.close()
        super().kill(nice)

    def get_session_info(self) -> dict:
        with self:
            output = self.session.get(
                self.bakalariAPI.get_endpoint(Endpoint.SESSION_INFO)
            ).json()
        return output

    def login(self) -> bool:
        with self:
            output = self.session.post(
                self.bakalariAPI.get_endpoint(Endpoint.LOGIN),
                {
                    "username": self.bakalariAPI.username,
                    "password": self.bakalariAPI.password,
                },
                allow_redirects=False,
            ).is_redirect
        return output

    def is_logged(self) -> bool:
        with self:
            response = self.session.get(
                self.bakalariAPI.get_endpoint(Endpoint.DASHBOARD), allow_redirects=False
            )
        return not response.is_redirect

    def get(self, *args, **kwargs) -> requests.Response:
        """Stejné jako `.session.get()`"""
        return self.session.get(*args, **kwargs)

    def post(self, *args, **kwargs) -> requests.Response:
        """Stejné jako `.session.post()`"""
        return self.session.post(*args, **kwargs)


class SeleniumSession(BakalariSession):
    """Session využívající Selenium."""

    def __init__(
        self,
        bakalariAPI: BakalariAPI,
        setBusy: bool = True,
        login: bool = True,
        enable_requests_acceleration: bool = True,
    ):
        if bakalariAPI.selenium_handler is None:
            raise exceptions.MissingSeleniumHandlerError()
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
            with self:
                self.session.get(self.bakalariAPI.get_endpoint(Endpoint.SESSION_INFO))
                output = json.loads(self.session.page_source)
            return output

    def extend(self):
        if self.requests_acceleration:
            requests.get(
                self.bakalariAPI.get_endpoint(Endpoint.SESSION_EXTEND),
                cookies=utils.cookies_webdriver2requests(self.session),
            )
        else:
            with self:
                self.session.get(self.bakalariAPI.get_endpoint(Endpoint.SESSION_EXTEND))

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
            response = requests.post(
                self.bakalariAPI.get_endpoint(Endpoint.LOGIN),
                {
                    "username": self.bakalariAPI.username,
                    "password": self.bakalariAPI.password,
                },
                allow_redirects=False,
            )
            if response.is_redirect:
                with self:
                    cookies = utils.cookies_requests2webdriver(response.cookies)

                    # Musíme být na správné stránce, jelikož jinak se nám vrátí error o špatné doméně,
                    # kterou si to případně domyslí, když je na dané stránce I guess a asi není nejlepší
                    # řešení dávat doménu "na tvrdo" (domain = bakalariAPI.url), takže to je (zatím) takto
                    self.session.get(self.bakalariAPI.get_endpoint(Endpoint.LOGIN))
                    for cookie in cookies:
                        self.session.add_cookie(cookie)
                return True
            else:
                return False
        else:
            with self:
                self.session.get(self.bakalariAPI.get_endpoint(Endpoint.LOGIN))
                self.session.find_element_by_id("username").send_keys(
                    self.bakalariAPI.username
                )
                self.session.find_element_by_id("password").send_keys(
                    self.bakalariAPI.password
                )
                self.session.find_element_by_id("loginButton").click()
                output = self.session.current_url != self.bakalariAPI.get_endpoint(
                    Endpoint.LOGIN
                )
            return output

    def is_logged(self) -> bool:
        if self.requests_acceleration:
            response = requests.get(
                self.bakalariAPI.get_endpoint(Endpoint.DASHBOARD),
                cookies=utils.cookies_webdriver2requests(self.session),
                allow_redirects=False,
            )
            return not response.is_redirect
        else:
            with self:
                self.session.get(self.bakalariAPI.get_endpoint(Endpoint.DASHBOARD))
                output = self.session.current_url == self.bakalariAPI.get_endpoint(
                    Endpoint.DASHBOARD
                )
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
            Pokud `True`, automaticky u sessionů zapne `auto_extend()` v nové daemon threadu.
            Pokud `False`, tak nic.
            Default je `False`, jelikož ve většině případů session přežije po potřebnou dobu i bez `extend()`
            a zbytečně se nevytvářejí theady.
    """

    def __init__(self, ref: BakalariAPI, start_auto_extend: bool = False):
        self.__lock = Lock()
        self.bakalariAPI: BakalariAPI = ref
        self.sessions: dict[type[BakalariSession], list[BakalariSession]] = {}
        self.start_auto_extend: bool = start_auto_extend
        atexit.register(self.kill_all, False)

    def create_session(self, session_class: type[Session], set_busy=True) -> Session:
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
        self, session_class: type[Session], set_busy=True, filter_busy=True
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
        with self.__lock:
            if session_class not in self.sessions:
                return None
            for session in self.sessions[session_class]:
                if not (filter_busy and session.busy):
                    session.busy = set_busy
                    # Tady `cast` prostě být musí, protože nelze udělat "inteligentní" `dict`, kde každý klíč má určitý typ,
                    # ale pokud je správná logika přidávání sessionů do `self.sessions`, tak jsme v pohodě.
                    # TODO: BTW když tak nad tím přemýšlím - každý klíč může mít jiný typ... Máme přeci `TypedDict`,
                    # takže jeden problém vyřešen. Druhý problém je ale ten, že by bylo fajn to mít dynamické dle,
                    # definovaných tříd které derivují z `BakalariSession. A kdyby to nešlo, tak bych rád zkusil
                    # udělat statický, jak to s tím půjde - přeci jen se to týká dvou tříd a na typování `self.sessions`,
                    # závisí pouze tento script.
                    return cast(Session, session)
        return None

    def get_session_or_create(
        self, session_class: type[Session], set_busy=True, filter_busy=True
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

    def kill_all(self, nice: bool = True, session_class: type[Session] | None = None):
        """Ukončí všechny sessiony.

        Argumenty:
            nice:
                Měly by se ukončit "mírumilovně"? (Default: True)
                (Pro význam slova "mírumilovně" viz BakalariSession.kill())
            session_class:
                Typ sessionů, které se mají ukončit; Pokud je None, ukončí se všechny. (Default: None)
        """
        with self.__lock:
            if session_class is None:
                for sessions in self.sessions.values():
                    for session in sessions:
                        session.kill(nice)
                self.sessions = {}
            else:
                for session in self.sessions[session_class]:
                    session.kill(nice)
                del self.sessions[session_class]

    def kill_dead(self, session_class: type[Session] | None = None):
        """Ukončí všechny sessiony, které jsou již odhlášeni z Bakalářů.

        Argumenty:
            session_class:
                Typ sessionů, které se mají ukončit; Pokud je None, ukončí se všechny. (Default: None)
        """
        with self.__lock:
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
