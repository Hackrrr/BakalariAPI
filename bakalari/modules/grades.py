"""Modul obsahující funkce týkající se známek."""
import json
from datetime import datetime

from bs4 import BeautifulSoup

from ..bakalari import BakalariAPI, Endpoint, RequestsSession, ResultSet, GetterOutput
from ..bakalariobjects import Grade


def getter(bakalariAPI: BakalariAPI, from_date: datetime = None) -> GetterOutput:
    """Získá dané známky."""
    session = bakalariAPI.session_manager.get_session(RequestsSession)
    response = session.get(bakalariAPI.get_endpoint(Endpoint.GRADES) + ("" if from_date is None else f"?dfrom={from_date.strftime('%Y%m%d')}0000&subt=obdobi"))
    session.busy = False
    return GetterOutput(GetterOutput.Types.SOUP, Endpoint.GRADES, BeautifulSoup(response.content, "html.parser"))

@BakalariAPI.register_parser(Endpoint.GRADES)
def parser(getter_output: GetterOutput) -> ResultSet:
    """Parsuje stránku se známkami."""
    output = ResultSet()
    znamky_list = getter_output.data("div", attrs={"data-clasif": True})
    for znamka in znamky_list:
        data = json.loads(znamka["data-clasif"])
        output.add_loot(Grade(
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
            data["typ"]
        ))
    return output
