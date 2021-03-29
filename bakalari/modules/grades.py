import json
from datetime import datetime

from bs4 import BeautifulSoup

from ..bakalari import BakalariAPI, Endpoint, RequestsSession, bakalarilootable_extension
from ..bakalariobjects import Grade


@bakalarilootable_extension
def get_grades(bakalariAPI: BakalariAPI, from_date: datetime = None) -> list[Grade]:
    """Získá dané známky."""
    output = []

    session = bakalariAPI.session_manager.get_session(RequestsSession)
    response = session.get(bakalariAPI.get_endpoint(Endpoint.GRADES) + ("" if from_date is None else f"?dfrom={from_date.strftime('%Y%m%d')}0000&subt=obdobi"))
    session.busy = False

    soup = BeautifulSoup(response.content, "html.parser")
    znamky_list = soup("div", attrs={"data-clasif": True})
    for znamka in znamky_list:
        data = json.loads(znamka["data-clasif"])
        output.append(Grade(
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

@bakalarilootable_extension
def get_all_grades(bakalariAPI: BakalariAPI) -> list[Grade]:
    """Získá všechny znímky."""
    return bakalariAPI.get_grades(datetime(1, 1, 1))
