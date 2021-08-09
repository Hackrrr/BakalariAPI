"""Modul obsahující funkce týkající se online schůzek."""
import json
from datetime import datetime

from bs4 import BeautifulSoup, Tag
from typing import cast

from ..bakalari import BakalariAPI, Endpoint, _register_parser, _register_resolver
from ..exceptions import BakalariQuerrySuccessError, MissingElementError
from ..looting import GetterOutput, ResultSet
from ..objects import Meeting, MeetingProvider, Student, UnresolvedID
from ..sessions import RequestsSession
from ..utils import line_iterator


def getter_meeting(bakalariAPI: BakalariAPI, ID: str) -> GetterOutput[dict]:
    """Získá schůzku s daným ID."""
    with bakalariAPI.session_manager.get_session_or_create(RequestsSession) as session:
        response = session.get(
            bakalariAPI.get_endpoint(Endpoint.MEETINGS_INFO) + ID
        ).json()
    return GetterOutput(Endpoint.MEETINGS_INFO, response)


def getter_future_meetings_ids(bakalariAPI: BakalariAPI) -> GetterOutput[BeautifulSoup]:
    """Získá IDčka budoucích schůzek."""
    with bakalariAPI.session_manager.get_session_or_create(RequestsSession) as session:
        response = session.get(bakalariAPI.get_endpoint(Endpoint.MEETINGS_OVERVIEW))
    return GetterOutput(
        Endpoint.MEETINGS_OVERVIEW, BeautifulSoup(response.content, "html.parser")
    )


def getter_meetings_ids(
    bakalariAPI: BakalariAPI, from_date: datetime, to_date: datetime
) -> GetterOutput[dict]:
    """Získá IDčka daných schůzek."""
    with bakalariAPI.session_manager.get_session_or_create(RequestsSession) as session:
        response = session.post(
            bakalariAPI.get_endpoint(Endpoint.MEETINGS_OVERVIEW),
            {
                "TimeWindow": "FromTo",
                "FilterByAuthor": "AllInvitations",
                "MeetingFrom": from_date.strftime("%Y-%m-%dT%H:%M:%S") + "+00:00",
                "MeetingTo": to_date.strftime("%Y-%m-%dT%H:%M:%S") + "+00:00",
            },
        ).json()
    return GetterOutput(Endpoint.MEETINGS_OVERVIEW, response)


@_register_parser(Endpoint.MEETINGS_OVERVIEW, BeautifulSoup)
def parser_meetings_overview_html(
    getter_output: GetterOutput[BeautifulSoup],
) -> ResultSet:
    output = ResultSet()
    if getter_output.data.head is None:
        raise MissingElementError("head")
    scritps = cast(Tag, getter_output.data.head)("script")
    formated = ""
    for script in scritps:
        formated = cast(Tag, script).prettify()
        if "var model = " in formated:
            break
    loot = {"Meetings": False, "Students": False}
    for line in line_iterator(formated):
        line = line.strip()
        if line.startswith("var meetingsData = "):
            loot["Meetings"] = True
            meetings_json = json.loads(line.strip()[len("var meetingsData = ") : -1])
            for meeting in meetings_json:
                output.add_loot(UnresolvedID(str(meeting["Id"]), Meeting))
        elif line.startswith("model.Students = ko.mapping.fromJS("):
            loot["Students"] = True
            students_json = json.loads(
                line.strip()[len("model.Students = ko.mapping.fromJS(") : -2]
            )
            for student in students_json:
                output.add_loot(
                    Student(
                        student["Id"],
                        student["Name"],
                        student["Surname"],
                        student["Class"],
                    )
                )
        if loot["Meetings"] and loot["Students"]:
            break
    return output


@_register_parser(Endpoint.MEETINGS_OVERVIEW, dict)
def parser_meetings_overview_json(getter_output: GetterOutput[dict]) -> ResultSet:
    output = ResultSet()
    for meeting in getter_output.data["data"]["Meetings"]:
        output.add_loot(UnresolvedID(str(meeting["Id"]), Meeting))
    return output


@_register_parser(Endpoint.MEETINGS_INFO, dict)
def parser_meetings_info(getter_output: GetterOutput[dict]) -> ResultSet:
    obj = getter_output.data
    if not obj["success"]:
        raise BakalariQuerrySuccessError(
            "Dotaz na endpoint MEETINGS_INFO skončil neúspěchem - schůzka byla v minulosti vytvořena ale pravděpodobně nebyla správně vymazána"
        )
    return ResultSet(
        Meeting(
            str(
                obj["data"]["Id"]
            ),  # Actually je to int, ale všechny ostaní IDčka jsou string, takže se budeme tvářit že je string i tohle...
            obj["data"]["OwnerId"],
            obj["data"]["Title"],
            obj["data"]["Details"],
            datetime.strptime(obj["data"]["MeetingStart"], "%Y-%m-%dT%H:%M:%S%z"),
            datetime.strptime(obj["data"]["MeetingEnd"], "%Y-%m-%dT%H:%M:%S%z"),
            obj["data"]["JoinMeetingUrl"],
            [(s["PersonId"], s["PersonName"]) for s in obj["data"]["Participants"]],
            [
                (
                    s["PersonId"],
                    datetime.strptime(
                        s["Readed"][: -(len(s["Readed"]) - s["Readed"].rfind("."))],
                        "%Y-%m-%dT%H:%M:%S",
                    ),
                )
                for s in obj["data"]["ParticipantsListOfRead"]
            ],
            MeetingProvider.BY_ID[int(obj["data"]["MeetingProviderId"])],
        )
    )


@_register_resolver(Meeting)
def resolver(bakalariAPI: BakalariAPI, unresolved: UnresolvedID[Meeting]) -> Meeting:
    return parser_meetings_info(getter_meeting(bakalariAPI, unresolved.ID)).get(
        Meeting
    )[0]
