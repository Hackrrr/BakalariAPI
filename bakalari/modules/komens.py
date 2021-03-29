from datetime import datetime, timedelta

from bs4 import BeautifulSoup

from ..bakalari import BakalariAPI, Endpoint, RequestsSession, bakalariextension, bakalarilootable_extension
from ..bakalariobjects import Komens, KomensFile

#TODO: Komens2Meetings

@bakalariextension
def get_komens_IDs(bakalariAPI: BakalariAPI, from_date: datetime = None, to_date: datetime = None) -> list[str]:
    """Získá IDčka daných Komens zpráv."""
    output = []
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

    soup = BeautifulSoup(response.content, "html.parser")
    komens_list = soup.find(id="message_list_content").find("ul").find_all("li", recursive=False)
    for komens in komens_list:
        output.append(komens.find("table")["data-idmsg"])
    return output

@bakalariextension
def get_all_komens_IDs(bakalariAPI: BakalariAPI):
    """Získá IDčka všech přijatých Komens zpráv."""
    return bakalariAPI.get_komens_IDs(datetime(1953, 1, 1), datetime.today() + timedelta(1))


@bakalarilootable_extension
def get_komens(bakalariAPI: BakalariAPI, ID: str, context: str = "prijate") -> Komens:
    """Získá Komens zprávu s daným ID."""
    session = bakalariAPI.session_manager.get_session_or_create(RequestsSession)
    response = session.post(bakalariAPI.get_endpoint(Endpoint.KOMENS_GET), json={
        "idmsg": ID,
        "context": context
    }).json()
    session.busy = False

    soubory = []
    if len(response["Files"]) != 0:
        for soubor in response["Files"]:
            komens_file = KomensFile(
                soubor["id"],
                soubor["name"],
                soubor["Size"],
                soubor["type"],
                soubor["idmsg"],
                soubor["path"],
            )
            soubory.append(komens_file)
            #if soubor["idmsg"] != ID:
            #    warnings.warn(f"ID zprávy se neschoduje s ID zprávy referencované v souboru; ID zprávy: {ID}, ID v souboru: {soubor['idmsg']}", UnexpectedBehaviour)

    komens = Komens(
        ID,
        response["Jmeno"],
        response["MessageText"],
        datetime.strptime(response["Cas"], "%d.%m.%Y %H:%M"),
        response["MohuPotvrdit"],
        response["Potvrzeno"],
        response["Kind"],
        soubory
    )
    bakalariAPI.looting.add_loot_array(soubory)
    return komens
