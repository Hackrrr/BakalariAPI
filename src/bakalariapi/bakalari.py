"""Hlavní část BakalářiAPI. Tento modul obsahuje většinu věcí z celého BakalářiAPI.

Základem je třída BakalářiAPI, která by měla stačit pro "normální" užití.

Tento modul primárně implementuje:
    BakalariAPI - Základní třída na ovládání celého BakalářiAPI
    SeleniumHandler - "Pomocná" třída pomáhající k ovládání Selenia
    Browser - Enum podporovaných browserů pro Selenium
    Looting - Třída starající se o persistenci, uchování a částečné zpracování výsledků
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Type, overload

import requests
from bs4 import BeautifulSoup

LOGGER = logging.getLogger("bakalariapi")
LOGGER.addHandler(logging.NullHandler())

__version__ = "2.0.0"
__all__ = ["Endpoint", "BakalariAPI", "LAST_SUPPORTED_VERSION", "GetMode"]
LAST_SUPPORTED_VERSION = "1.41.506.1"


class Endpoint:
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


Endpoint._ENDPOINT_DICT = {
    name: path for name, path in Endpoint.__dict__.items() if not name.startswith("_")
}


_parsers: dict[
    str, dict[Any, list[Callable[[looting.GetterOutput], looting.ResultSet]]]
] = {x: {} for x in Endpoint._ENDPOINT_DICT.values()}
_resolvers: dict[
    Type[BakalariObject],
    list[Callable[[BakalariAPI, UnresolvedID], BakalariObject | None]],
] = {}


def _register_parser(endpoint: str, type_: Type[looting.GetterOutputTypeVar]):
    """Dekorátor, který zaregistruje funkci jako parser pro daný endpoint.

    Pro běžné užití BakalářiAPI není doporučeno tento dekorátor používat.
    Samotný dekorátor funkci nijak neupravuje.
    Dekorovaná funkce by měla brát GetterOutput (typu, který se passuje jako argument `type_` tohoto dekorátoru) a měla by vracet looting.ResultSet či None, pokud není schopná z daného GetterOutput(u) nic získat.

    Args:
        endpoint:
            Endpoint, který daná funkce umí parsovat.
        type_:
            Typ generické třídy GetterOutput, který funkce přijímá.
    """
    LOGGER.debug("New parser registred for endpoint '%s' (Type: %s)", endpoint, type_)

    def decorator(
        func: Callable[
            [looting.GetterOutput[looting.GetterOutputTypeVar]], looting.ResultSet
        ]
    ):
        _parsers[endpoint].setdefault(type_, []).append(func)
        return func

    return decorator


def _register_resolver(type_: Type[BakalariObj]):
    """Dekorátor, který zaregistruje funkci jako resolver pro daný typ.

    Pro běžné užití BakalářiAPI není doporučeno tento dekorátor používat.
    Samotný dekorátor funkci nijak neupravuje.
    Dekorovaná funkce by měla brát UnresolvedID a měla by vracet typ, který se passuje v argumentu `type_` tohoto dekorátoru nebo None, pokud funkce není schopná resolvovat dané UnresovedID.

    Args:
        type_:
            Typ/Třída, pro kterou je tato funkce resolverem.
    """
    LOGGER.debug("New resolver registred for type %s", type_)

    def decorator(
        func: Callable[[BakalariAPI, UnresolvedID[BakalariObj]], BakalariObj]
    ):
        _resolvers.setdefault(type_, []).append(func)
        return func

    return decorator


def _parse(
    getter_output: looting.GetterOutput[looting.GetterOutputTypeVar],
) -> looting.ResultSet:
    """Extrahují se data z GetterOutput insance za pomoci registrovaných parserů.

    Data získaná skrze tuto metodu jsou automaticky ukládána v looting instanci.
    Pro běžné užití BakalářiAPI není tato funkce nutná. Pokud nevíte, jestli tuto
    funkci máte/potřebujete použít, tak ji nepotřebujete.

    Args:
        getter_output:
            GetterOutput, ze kterého se mají data extrahovat.

    Returns:
        looting.ResultSet, který obsahuje všechna data od jednotlivých parserů.
    """
    output = looting.ResultSet()
    for parser in _parsers[getter_output.endpoint].setdefault(getter_output.type, []):
        parser_output = parser(getter_output)
        if parser_output is not None:
            output.merge(parser_output)
    return output


def _resolve(
    unresolved: UnresolvedID | list[UnresolvedID] | looting.ResultSet,
    bakalariAPI: BakalariAPI,
    silence_querry_errors: bool = False,
) -> looting.ResultSet:
    """Pokusí se získat plnohodnotný objekt pro dané UnresolvedID za pomoci registrovaných resolverů.

    Data získaná skrze tuto metodu jsou automaticky ukládána v looting instanci.
    Pro běžné užití BakalářiAPI není tato funkce nutná. Pokud nevíte, jestli tuto
    funkci máte/potřebujete použít, tak ji nepotřebujete.

    Args:
        unresolved:
            Jedno nebo více UnresolvedID, pro které se BakalářiAPI pokusí získat plnohodnotný objekt.

    Returns:
        looting.ResultSet, který obsahuje všechna data od jednotlivých resolverů.
    """
    if isinstance(unresolved, looting.ResultSet):
        output = unresolved
        unresolved = output.get(UnresolvedID)
        output.remove(UnresolvedID)
    else:
        output = looting.ResultSet()
        if not isinstance(unresolved, list):
            unresolved = [unresolved]

    for o in unresolved:
        if o.type in _resolvers:
            resolved = False
            for resolver in _resolvers[o.type]:
                try:
                    tmp = resolver(bakalariAPI, o)
                except exceptions.BakalariQuerrySuccessError as e:
                    if silence_querry_errors:
                        continue
                    raise e
                if tmp is not None:
                    output.add_loot(tmp)
                    resolved = True
                    break
            if not resolved:
                output.add_loot(o)
        else:
            output.add_loot(o)
    return output


class GetMode(Enum):
    """Enum určující mód při získávání dat.

    CACHED - Data se získají pouze z `Looting` instance
    FRESH - Data se získají pouze ze serveru
    CACHED_OR_FRESH - Nejprve se zkusí načíst data z `Looting` instance, pokud zde nejsou, načtou se data ze serveru
    """

    CACHED = 0
    FRESH = 1
    CACHED_OR_FRESH = 2


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

    def __init__(
        self,
        url: str,
        username: str = "",
        password: str = "",
        seleniumHandler: seleniumhandler.SeleniumHandler | None = None,
    ):
        self.username: str = username
        self.password: str = password
        self.selenium_handler: seleniumhandler.SeleniumHandler | None = seleniumHandler
        self.session_manager: sessions.SessionManager = sessions.SessionManager(
            self, True
        )
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
        session = self.session_manager.get_session_or_create(sessions.RequestsSession)
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
        session = self.session_manager.get_session_or_create(sessions.RequestsSession)

        getter_output = looting.GetterOutput(
            Endpoint.USER_INFO,
            BeautifulSoup(
                session.get(self.get_endpoint(Endpoint.USER_INFO)).content,
                "html.parser",
            ),
        )
        session.busy = False
        self._parse(getter_output)

        # Možná by se mohl registrovat parser
        data = json.loads(getter_output.data.head["data-pageinfo"])  # type: ignore # Jelikož "head" může být None, tak Pylance naříká
        self.user_info.type = data["userType"]
        self.user_info.hash = data["userHash"]
        self.server_info.version = data["applicationVersion"]
        self.server_info.version_date = datetime.strptime(data["appVersion"], "%Y%m%d")
        self.server_info.evid_number = int(data["evidNumber"])

    # GRADES
    @overload
    def get_grades(self, mode: GetMode.CACHED) -> list[Grade]:  # type: ignore
        """Načte a vrátí známky z vlastní looting instance.

        Returns:
            List známek, které byl získány v minulosti.
        """

    @overload
    def get_grades(self, mode: GetMode.FRESH, *, from_date: datetime | None = None) -> list[Grade]:  # type: ignore
        """Nově načte a vrátí známky.

        Args:
            from_date:
                Pokud není None, načtou se známky pouze od daného data (včetně).
                Pokud je None, načtou se známky pouze ze současného pololetí.

        Returns:
            Nově načtený list známek.
        """

    @overload
    def get_grades(self, mode: GetMode.CACHED_OR_FRESH, *, from_date: datetime | None = None) -> list[Grade]:  # type: ignore
        """Načte a vrátí známky z vlastní looting instance. Pokud v looting instanci nejsou přítomny žádné známky, pokusí se načíst nové.

        Pokud jsou známky přítomny v looting instanci, argumenty této metody jsou nepodstatné.

        Args:
            from_date:
                Pokud není None, načtou se známky pouze od daného data (včetně).
                Pokud je None, načtou se známky pouze ze současného pololetí.

        Returns:
            Načtený list známek.
        """

    def get_grades(self, mode: GetMode, **kwargs) -> list[Grade]:
        kwargs = {"from_date": None, **kwargs}
        if mode == GetMode.CACHED:
            return self.looting.get(Grade)
        elif mode == GetMode.FRESH:
            return self._parse(modules.grades.getter(self, kwargs["from_date"])).get(
                Grade
            )
        elif mode == GetMode.CACHED_OR_FRESH:
            output = self.get_grades(GetMode.CACHED)
            return (
                self.get_grades(GetMode.FRESH, **kwargs) if len(output) == 0 else output
            )

    def get_all_grades(self) -> list[Grade]:
        """Nově načte a vrátí všechny známky.

        Vždy načítá čerstvá data z Bakalářů.

        Returns:
            Nově načtený list všech známek.
        """
        return self.get_grades(GetMode.FRESH, from_date=datetime(1, 1, 1))

    # HOMEWORKS
    @overload
    def get_homeworks(self, mode: GetMode.CACHED) -> list[Homework]:  # type: ignore
        """Načte a vrátí úkoly z vlastní looting instance.

        Returns:
            List úkolů, které byl získány v minulosti.
        """

    @overload
    def get_homeworks(
        self,
        mode: GetMode.FRESH,  # type: ignore
        *,
        fast_mode: True,  # type: ignore
    ) -> list[Homework]:
        """Nově načte a vrátí úkoly.

        Args:
            fast_mode:
                Určuje mód načítání úkolů. Pokud je `True`, vykoná načtení úkolů v "rychlém módu".
                "Rychlý mód" načte úkoly podstatně rychleji než "pomalý mód", ale dokáže načíst pouze prvních 20 aktivních nehotových úkolů.
                Pokud `False`, načtení úkolů proběhne v "pomalém módu", který má více možností.

        Returns:
            Nově načtený list úkolů.
        """

    @overload
    def get_homeworks(
        self,
        mode: GetMode.FRESH,  # type: ignore
        *,
        fast_mode: False,  # type: ignore
        unfinished_only: bool = True,
        only_first_page: bool = False,
        first_loading_timeout: float = 5,
        second_loading_timeout: float = 10,
    ) -> list[Homework]:
        """Nově načte a vrátí úkoly.

        Args:
            fast_mode:
                Určuje mód načítání úkolů. Pokud je `True`, vykoná načtení úkolů v "rychlém módu".
                "Rychlý mód" načte úkoly podstatně rychleji než "pomalý mód", ale dokáže načíst pouze prvních 20 aktivních nehotových úkolů.
                Pokud `False`, načtení úkolů proběhne v "pomalém módu", který má více možností.
            unfinished_only:
                Pokud je `True`, načte pouze úkoly označené jako nehotové.
                Pokud je `False`, načte hotové i nehotové úkoly.
            only_first_page:
                Pokud je `True`, načte úkoly jen z první stránky na Bakalářích.
                Pokud je `False`, načte úkoly ze všech stránek.
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

    @overload
    def get_homeworks(
        self,
        mode: GetMode.CACHED_OR_FRESH,  # type: ignore
        *,
        fast_mode: True,  # type: ignore
    ) -> list[Homework]:
        """Načte a vrátí úkoly z vlastní looting instance. Pokud v looting instanci nejsou přítomny žádné úkoly, pokusí se načíst nové.

        Pokud jsou úkoly přítomny v looting instanci, argumenty této metody jsou nepodstatné.

        Args:
            fast_mode:
                Určuje mód načítání úkolů. Pokud je `True`, vykoná načtení úkolů v "rychlém módu".
                "Rychlý mód" načte úkoly podstatně rychleji než "pomalý mód", ale dokáže načíst pouze prvních 20 aktivních nehotových úkolů.
                Pokud `False`, načtení úkolů proběhne v "pomalém módu", který má více možností.

        Returns:
            Načtený list úkolů.
        """

    @overload
    def get_homeworks(
        self,
        mode: GetMode.CACHED_OR_FRESH,  # type: ignore
        *,
        fast_mode: False,  # type: ignore
        unfinished_only: bool = True,
        only_first_page: bool = False,
        first_loading_timeout: float = 5,
        second_loading_timeout: float = 10,
    ) -> list[Homework]:
        """Načte a vrátí úkoly z vlastní looting instance. Pokud v looting instanci nejsou přítomny žádné úkoly, pokusí se načíst nové.

        Pokud jsou úkoly přítomny v looting instanci, argumenty této metody jsou nepodstatné.

        Args:
            fast_mode:
                Určuje mód načítání úkolů. Pokud je `True`, vykoná načtení úkolů v "rychlém módu".
                "Rychlý mód" načte úkoly podstatně rychleji než "pomalý mód", ale dokáže načíst pouze prvních 20 aktivních nehotových úkolů.
                Pokud `False`, načtení úkolů proběhne v "pomalém módu", který má více možností.
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
            Načtený list úkolů.
        """

    def get_homeworks(self, mode: GetMode, **kwargs) -> list[Homework]:
        kwargs = {
            "unfinished_only": True,
            "only_first_page": False,
            "first_loading_timeout": 5,
            "second_loading_timeout": 10,
            **kwargs,
        }

        if mode == GetMode.CACHED:
            return self.looting.get(Homework)
        elif mode == GetMode.FRESH:
            if kwargs["fast_mode"]:
                return self._parse(modules.homeworks.getter_fast(self)).get(Homework)
            else:
                output = modules.homeworks.get_slow(
                    self,
                    kwargs["unfinished_only"],
                    kwargs["only_first_page"],
                    kwargs["first_loading_timeout"],
                    kwargs["second_loading_timeout"],
                )
                self.looting.add_result_set(output)
                return output.get(Homework)
        elif mode == GetMode.CACHED_OR_FRESH:
            output = self.get_homeworks(GetMode.CACHED)
            return (
                self.get_homeworks(GetMode.FRESH, **kwargs)
                if len(output) == 0
                else output
            )

    def get_all_homeworks(self) -> list[Homework]:
        """Nově načte a vrátí všechny úkoly.

        Vždy načítá čerstvá data z Bakalářů a načtení úkolů proběhne v "pomalém módu".

        Returns:
            Nově načtený list všech úkolů.
        """
        return self.get_homeworks(
            GetMode.FRESH, fast_mode=False, unfinished_only=False, only_first_page=False
        )

    # MEETINGS
    @overload
    def get_meetings(self, mode: GetMode.CACHED) -> list[Meeting]:  # type: ignore
        """Načte a vrátí schůzky z vlastní looting instance.

        Returns:
            List schůzek, které byl získány v minulosti.
        """

    @overload
    def get_meetings(self, mode: GetMode.FRESH) -> list[Meeting]:  # type: ignore
        """Nově načte a vrátí nadcházející schůzky.

        Returns:
            Nově načtený list nadcházejících schůzek.
        """

    @overload
    def get_meetings(self, mode: GetMode.FRESH, *, from_date: datetime, to_date: datetime) -> list[Meeting]:  # type: ignore
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

    @overload
    def get_meetings(self, mode: GetMode.CACHED_OR_FRESH) -> list[Meeting]:  # type: ignore
        """Načte a vrátí schůzky z vlastní looting instance. Pokud v looting instanci nejsou přítomny žádné schůzky, pokusí se načíst nové nadchézející schůzky.

        Returns:
            Načtený list schůzek.
        """

    @overload
    def get_meetings(self, mode: GetMode.CACHED_OR_FRESH, *, from_date: datetime, to_date: datetime) -> list[Meeting]:  # type: ignore
        """Načte a vrátí schůzky z vlastní looting instance. Pokud v looting instanci nejsou přítomny žádné schůzky, pokusí se načíst nové.

        Je nutné specifikovat horní i dolní časovou hranici. Nejmenší možný čas je `datetime(1, 1, 1)`, největší možný je `datetime(9999, 12, 31, 23, 59, 59)`.
        Pokud jsou schůzky přítomny v looting instanci, argumenty této metody jsou nepodstatné.

        Args:
            from_date:
                Určuje datum a čas, od kterého se mají schůzky načíst.
            to_date:
                Určuje datum a čas, do kterého se mají schůzky načíst.

        Returns:
            Načtený list schůzek.
        """

    def get_meetings(self, mode: GetMode, **kwargs) -> list[Meeting]:
        if mode == GetMode.CACHED:
            return self.looting.get(Meeting)
        elif mode == GetMode.FRESH:
            if "from_date" in kwargs:
                return self._resolve(
                    self._parse(
                        modules.meetings.getter_meetings_ids(
                            self, kwargs["from_date"], kwargs["to_date"]
                        )
                    )
                ).get(Meeting)
            else:
                return self._resolve(
                    self._parse(modules.meetings.getter_future_meetings_ids(self)).get(
                        UnresolvedID
                    )
                ).get(Meeting)
        elif mode == GetMode.CACHED_OR_FRESH:
            output = self.get_meetings(GetMode.CACHED)
            return (
                self.get_meetings(GetMode.FRESH, **kwargs)
                if len(output) == 0
                else output
            )

    def get_all_meetings(self) -> list[Meeting]:
        """Nově načte a vrátí všechny schůzky.

        Vždy načítá čerstvá data z Bakalářů.

        Returns:
            Nově načtený list všech schůzek.
        """
        return self.get_meetings(
            GetMode.FRESH,
            from_date=datetime(1, 1, 1),
            to_date=datetime(9999, 12, 31, 23, 59, 59),
        )

    # STUDENTS
    @overload
    def get_students(self, mode: GetMode.CACHED) -> list[Student]:  # type: ignore
        """Načte a vrátí studenty z vlastní looting instance.

        Returns:
            List studentů, kteří byl získány v minulosti.
        """

    @overload
    def get_students(self, mode: GetMode.FRESH) -> list[Student]:  # type: ignore
        """Nově načte a vrátí seznam studentů.

        Returns:
            Nově načtený list studentů.
        """

    @overload
    def get_students(self, mode: GetMode.CACHED_OR_FRESH) -> list[Student]:  # type: ignore
        """Načte a vrátí studenty z vlastní looting instance. Pokud v looting instanci nejsou přítomny žádní studenti, pokusí se načíst nové.

        Returns:
            Načtený list studentů.
        """

    def get_students(self, mode: GetMode, **kwargs) -> list[Student]:
        if mode == GetMode.CACHED:
            return self.looting.get(Student)
        elif mode == GetMode.FRESH:
            return self._parse(modules.meetings.getter_future_meetings_ids(self)).get(
                Student
            )
        elif mode == GetMode.CACHED_OR_FRESH:
            output = self.get_students(GetMode.CACHED)
            return (
                self.get_students(GetMode.FRESH, **kwargs)
                if len(output) == 0
                else output
            )

    # KOMENS
    @overload
    def get_komens(self, mode: GetMode.CACHED) -> list[Komens]:  # type: ignore
        """Načte a vrátí komens zprávy z vlastní looting instance.

        Returns:
            List komens zpráv, které byl získány v minulosti.
        """

    @overload
    def get_komens(
        self,
        mode: GetMode.FRESH,  # type: ignore
        *,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        limit: int | None = None,
    ) -> list[Komens]:
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

    @overload
    def get_komens(
        self,
        mode: GetMode.CACHED_OR_FRESH,  # type: ignore
        *,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        limit: int | None = None,
    ) -> list[Komens]:
        """Načte a vrátí komens zprávy z vlastní looting instance. Pokud v looting instanci nejsou přítomny žádné komens zprávy, pokusí se načíst nové.

        Kvůli limitaci Bakalářů je možné případně načíst pouze 300 zpráv na jednou.
        Pokud jsou schůzky přítomny v looting instanci, argumenty této metody jsou nepodstatné.

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
            Načtený list komens zpráv.
        """

    def get_komens(self, mode: GetMode, **kwargs) -> list[Komens]:
        kwargs = {"from_date": None, "to_date": None, "limit": None, **kwargs}

        if mode == GetMode.CACHED:
            return self.looting.get(Komens)
        elif mode == GetMode.FRESH:
            return self._resolve(
                self._parse(
                    modules.komens.getter_komens_ids(
                        self, kwargs["from_date"], kwargs["to_date"]
                    )
                ).get(UnresolvedID)[: kwargs["limit"]]
            ).get(Komens)
        elif mode == GetMode.CACHED_OR_FRESH:
            output = self.get_komens(GetMode.CACHED)
            return (
                self.get_komens(GetMode.FRESH, **kwargs) if len(output) == 0 else output
            )

    def get_all_komens(self) -> list[Komens]:
        """Nově načte a vrátí všechny komens zprávy.

        Vždy načítá čerstvá data z Bakalářů.
        Kvůli limitaci Bakalářů je možné načíst pouze 300 zpráv na jednou.

        Returns:
            Nově načtený list všech komens zpráv.
        """
        return self.get_komens(
            GetMode.FRESH,
            from_date=datetime(1953, 1, 1),
            to_date=datetime.today() + timedelta(1),
        )

    def _parse(
        self, getter_output: looting.GetterOutput[looting.GetterOutputTypeVar]
    ) -> looting.ResultSet:
        """Extrahují se data z GetterOutput insance za pomoci registrovaných parserů.

        Data získaná skrze tuto metodu jsou automaticky ukládána v looting instanci.
        Pro běžné užití BakalářiAPI není tato funkce nutná. Pokud nevíte, jestli tuto
        funkci máte/potřebujete použít, tak ji nepotřebujete.

        Args:
            getter_output:
                GetterOutput, ze kterého se mají data extrahovat.

        Returns:
            ResultSet, který obsahuje všechna data od jednotlivých parserů.
        """
        output = _parse(getter_output)
        self.looting.add_result_set(output)
        return output

    def _resolve(
        self,
        unresolved: UnresolvedID | list[UnresolvedID] | looting.ResultSet,
        silence_querry_errors: bool = False,
    ) -> looting.ResultSet:
        """Pokusí se získat plnohodnotný objekt pro dané UnresolvedID za pomoci registrovaných resolverů.

        Data získaná skrze tuto metodu jsou automaticky ukládána v looting instanci.
        Pro běžné užití BakalářiAPI není tato funkce nutná. Pokud nevíte, jestli tuto
        funkci máte/potřebujete použít, tak ji nepotřebujete.

        Args:
            unresolved:
                Jedno nebo více UnresolvedID, pro které se BakalářiAPI pokusí získat plnohodnotný objekt.

        Returns:
            ResultSet, který obsahuje všechna data od jednotlivých resolverů.
        """
        output = _resolve(unresolved, self, silence_querry_errors)
        self.looting.add_result_set(output)
        return output


from . import exceptions, looting, modules, seleniumhandler, sessions
from .objects import (
    BakalariObj,
    BakalariObject,
    Grade,
    Homework,
    Komens,
    Meeting,
    ServerInfo,
    Student,
    UnresolvedID,
    UserInfo,
)
