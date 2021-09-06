"""Modul obsahující funkce týkající se známek."""
import json
from datetime import datetime
from typing import cast

from bs4 import BeautifulSoup
from bs4.element import Tag  # Kvůli mypy - https://github.com/python/mypy/issues/10826

from ..bakalari import BakalariAPI, Endpoint, _register_parser
from ..looting import GetterOutput, ResultSet
from ..objects import Grade
from ..sessions import RequestsSession
from ..utils import parseHTML


def getter(
    bakalariAPI: BakalariAPI, from_date: datetime = None
) -> GetterOutput[BeautifulSoup]:
    """Získá dané známky."""
    with bakalariAPI.session_manager.get_session_or_create(RequestsSession) as session:
        response = session.get(
            bakalariAPI.get_endpoint(Endpoint.GRADES)
            + (
                ""
                if from_date is None
                else f"?dfrom={from_date.strftime('%Y%m%d')}0000&subt=obdobi"
            )
        )
    return GetterOutput(Endpoint.GRADES, parseHTML(response.content))


@_register_parser(Endpoint.GRADES, BeautifulSoup)
def parser(getter_output: GetterOutput[BeautifulSoup]) -> ResultSet:
    """Parsuje stránku se známkami."""
    output = ResultSet()
    znamky_list = cast(
        list[Tag], getter_output.data("div", attrs={"data-clasif": True})
    )
    for znamka in znamky_list:
        # `cast()` jelikož některé atributy mohou být multi-valued, tak zde je možný typ __getitem__ i `list`.
        # Ale tyto atributy jsou natrvdo předdefinované a "data-clasif" mezi nimi není.
        data = json.loads(cast(str, znamka["data-clasif"]))
        output.add_loot(
            Grade(
                data["id"],
                data["nazev"],
                data["MarkText"],
                data["vaha"],
                data["caption"],
                data["poznamkakzobrazeni"],
                data["MarkTooltip"] if data["MarkTooltip"] is not None else "",
                datetime.strptime(data["strdatum"], "%d.%m.%Y"),
                datetime.strptime(data["udel_datum"], "%d.%m.%Y"),
                data["strporadivetrideuplne"],
                data["typ"],
            )
        )
    return output
