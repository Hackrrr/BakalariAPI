"""Modul obsahující funkce týkající se Komens zpráv."""
from __future__ import annotations

from datetime import datetime
from typing import cast

from bs4 import BeautifulSoup
from bs4.element import Tag  # Kvůli mypy - https://github.com/python/mypy/issues/10826

from ..bakalari import BakalariAPI, Endpoint, _register_parser, _register_resolver
from ..exceptions import MissingElementError
from ..looting import GetterOutput, ResultSet
from ..objects import Komens, KomensFile, UnresolvedID
from ..sessions import RequestsSession
from ..utils import parseHTML


def getter_komens_ids(
    bakalariAPI: BakalariAPI,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
) -> GetterOutput[BeautifulSoup]:
    """Získá IDčka daných Komens zpráv.

    Kvůli limitaci Bakalářů je možné načíst pouze 300 zpráv na jednou.
    """
    target = bakalariAPI.get_endpoint(Endpoint.KOMENS)

    if from_date is not None or to_date is not None:
        target += "?s=custom"
        if from_date is not None:
            target += "&from=" + from_date.strftime("%d%m%Y")
        if to_date is not None:
            target += "&to=" + to_date.strftime("%d%m%Y")

    with bakalariAPI.session_manager.get_session_or_create(RequestsSession) as session:
        response = session.get(target)
    return GetterOutput(Endpoint.KOMENS, parseHTML(response.content))


def getter_info(
    bakalariAPI: BakalariAPI, ID: str, context: str = "prijate"
) -> GetterOutput[dict]:
    with bakalariAPI.session_manager.get_session_or_create(RequestsSession) as session:
        response = session.post(
            bakalariAPI.get_endpoint(Endpoint.KOMENS_GET),
            json={"idmsg": ID, "context": context},
        ).json()
    return GetterOutput(Endpoint.KOMENS_GET, response)


@_register_parser(Endpoint.KOMENS, BeautifulSoup)
def parser_main(getter_output: GetterOutput[BeautifulSoup]) -> ResultSet:
    output = ResultSet()

    # None-aware je deferred... Sadge
    # komens_list = getter_output.data.find(id="message_list_content")?.find("ul")?.find_all("li", recursive=False)

    x = getter_output.data.find(id="message_list_content")
    if x is None:
        raise MissingElementError('find(id="message_list_content")')
    x = cast(Tag, x.find("ul"))
    if x is None:
        raise MissingElementError('find(id="message_list_content").find("ul")')
    # `cast()` protože `find()` může najít i NavigableString, který ale nemá `find_all()` (teda ho nemůžeme volat)...
    komens_list = cast(list[Tag], x("li", recursive=False))

    for komens in komens_list:
        table = cast(Tag, komens.find("table"))
        if table is None:
            raise MissingElementError('komens.find("table")')
        # `cast()` na string, protože atribut může být i multivalued (=> list), což by ale u "data-idmsg" hrozit nemělo
        output.add_loot(UnresolvedID(cast(str, table["data-idmsg"]), Komens))
    return output


@_register_parser(Endpoint.KOMENS_GET, dict)
def parser_info(getter_output: GetterOutput[dict]) -> ResultSet:
    jsn = getter_output.data
    output = ResultSet()
    if len(jsn["Files"]) != 0:
        for soubor in jsn["Files"]:
            komens_file = KomensFile(
                soubor["id"],
                soubor["name"],
                soubor["Size"],
                soubor["type"],
                soubor["idmsg"],
                soubor["path"],
            )
            output.add_loot(komens_file)
    return output.add_loot(
        Komens(
            jsn["Id"],
            jsn["Jmeno"],
            jsn["MessageText"],
            datetime.strptime(jsn["Cas"], "%d.%m.%Y %H:%M"),
            jsn["MohuPotvrdit"],
            jsn["Potvrzeno"],
            jsn["Kind"],
            output.get(KomensFile),
        )
    )


@_register_resolver(Komens)
def resolver(bakalariAPI: BakalariAPI, unresolved: UnresolvedID) -> Komens:
    return parser_info(getter_info(bakalariAPI, unresolved.ID)).get(Komens)[0]
