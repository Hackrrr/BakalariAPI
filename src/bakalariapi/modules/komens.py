"""Modul obsahující funkce týkající se Komens zpráv."""
from datetime import datetime

from bs4 import BeautifulSoup

from ..bakalari import BakalariAPI, Endpoint, _register_parser, _register_resolver
from ..looting import GetterOutput, ResultSet
from ..objects import Komens, KomensFile, UnresolvedID
from ..sessions import RequestsSession


def getter_komens_ids(
    bakalariAPI: BakalariAPI, from_date: datetime = None, to_date: datetime = None
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

    session = bakalariAPI.session_manager.get_session_or_create(RequestsSession)
    response = session.get(target)
    session.busy = False
    return GetterOutput(Endpoint.KOMENS, BeautifulSoup(response.content, "html.parser"))


def getter_info(
    bakalariAPI: BakalariAPI, ID: str, context: str = "prijate"
) -> GetterOutput[dict]:
    session = bakalariAPI.session_manager.get_session_or_create(RequestsSession)
    response = session.post(
        bakalariAPI.get_endpoint(Endpoint.KOMENS_GET),
        json={"idmsg": ID, "context": context},
    ).json()
    session.busy = False
    return GetterOutput(Endpoint.KOMENS_GET, response)


@_register_parser(Endpoint.KOMENS, BeautifulSoup)
def parser_main(getter_output: GetterOutput[BeautifulSoup]) -> ResultSet:
    output = ResultSet()
    komens_list = (
        getter_output.data.find(id="message_list_content")
        .find("ul")  # type: ignore # Jelikož může být None, tak Pylance naříká
        .find_all("li", recursive=False)
    )
    for komens in komens_list:
        output.add_loot(UnresolvedID(komens.find("table")["data-idmsg"], Komens))
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
