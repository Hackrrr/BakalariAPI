import json
from datetime import datetime

from bs4 import BeautifulSoup

from ..bakalari import BakalariAPI, Endpoint, RequestsSession, ResultSet, GetterOutput
from ..utils import line_iterator
from ..bakalariobjects import Meeting, Student, UnresolvedID, MeetingProvider


def getter_meeting(bakalariAPI: BakalariAPI, ID: str) -> GetterOutput:
    """Získá schůzku s daným ID."""
    session = bakalariAPI.session_manager.get_session_or_create(RequestsSession, True)
    response = session.get(bakalariAPI.get_endpoint(Endpoint.MEETINGS_INFO) + ID).json()
    session.busy = False
    return GetterOutput(Endpoint.MEETINGS_INFO, response)

def getter_future_meetings_ids(bakalariAPI: BakalariAPI) -> GetterOutput:
    """Získá IDčka budoucích schůzek."""
    session = bakalariAPI.session_manager.get_session_or_create(RequestsSession, True)
    response = session.get(bakalariAPI.get_endpoint(Endpoint.MEETINGS_OVERVIEW))
    session.busy = False
    return GetterOutput(Endpoint.MEETINGS_OVERVIEW, BeautifulSoup(response.content, "html.parser"))

def getter_meetings_ids(bakalariAPI: BakalariAPI, from_date: datetime, to_date: datetime) -> GetterOutput:
    """Získá IDčka daných schůzek."""
    session = bakalariAPI.session_manager.get_session_or_create(RequestsSession, True)
    response = session.post(bakalariAPI.get_endpoint(Endpoint.MEETINGS_OVERVIEW), {
        "TimeWindow": "FromTo",
        "FilterByAuthor": "AllInvitations",
        "MeetingFrom": from_date.strftime("%Y-%m-%dT%H:%M:%S") + "+00:00",
        "MeetingTo": to_date.strftime("%Y-%m-%dT%H:%M:%S") + "+00:00"
    }).json()
    session.busy = False
    return GetterOutput(Endpoint.MEETINGS_OVERVIEW, response)





@BakalariAPI.register_parser(Endpoint.MEETINGS_OVERVIEW, BeautifulSoup)
def parser_meetings_overview_html(getter_output: GetterOutput[BeautifulSoup]) -> ResultSet:
    output = ResultSet()
    scritps = getter_output.data.head("script")
    formated = ""
    for script in scritps:
        formated = script.prettify()
        if "var model = " in formated:
            break
    loot = {
        "Meetings": False,
        "Students": False
    }
    for line in line_iterator(formated):
        line = line.strip()
        if line.startswith("var meetingsData = "):
            loot["Meetings"] = True
            meetingsJSON = json.loads(line.strip()[len("var meetingsData = "):-1])
            for meeting in meetingsJSON:
                output.add_loot(UnresolvedID(str(meeting["Id"]), Meeting)) # Actually je to int, ale všechny ostaní IDčka jsou string, takže se budeme tvářit že je string i tohle...
        elif line.startswith("model.Students = ko.mapping.fromJS("):
            loot["Students"] = True
            studentsJSON = json.loads(line.strip()[len("model.Students = ko.mapping.fromJS("):-2])
            for student in studentsJSON:
                output.add_loot(Student(
                    student["Id"],
                    student["Name"],
                    student["Surname"],
                    student["Class"]
                ))
        if loot["Meetings"] and loot["Students"]:
            break
    return output
@BakalariAPI.register_parser(Endpoint.MEETINGS_OVERVIEW, dict)
def parser_meetings_overview_json(getter_output: GetterOutput[dict]) -> ResultSet:
    output = ResultSet()
    for meeting in getter_output.data["data"]["Meetings"]:
        output.add_loot(UnresolvedID(str(meeting["Id"]), Meeting))
    return output

@BakalariAPI.register_parser(Endpoint.MEETINGS_INFO, dict)
def parser_meetings_info(getter_output: GetterOutput[dict]) -> ResultSet:
    obj = getter_output.data
    return ResultSet(Meeting(
        str(obj["data"]["Id"]), # Actually je to int, ale všechny ostaní IDčka jsou string, takže se budeme tvářit že je string i tohle...
        obj["data"]["OwnerId"],
        obj["data"]["Title"],
        obj["data"]["Details"],
        datetime.strptime(obj["data"]["MeetingStart"], "%Y-%m-%dT%H:%M:%S%z"),
        datetime.strptime(obj["data"]["MeetingEnd"], "%Y-%m-%dT%H:%M:%S%z"),
        obj["data"]["JoinMeetingUrl"],
        [(s["PersonId"], s["PersonName"]) for s in obj["data"]["Participants"]],
        [(s["PersonId"], datetime.strptime(s["Readed"][:-(len(s["Readed"]) - s["Readed"].rfind("."))], "%Y-%m-%dT%H:%M:%S")) for s in obj["data"]["ParticipantsListOfRead"]],
        MeetingProvider.BY_ID[int(obj["data"]["MeetingProviderId"])]
    ))

@BakalariAPI.register_resolver(Meeting)
def resolver(bakalariAPI: BakalariAPI, unresolved: UnresolvedID) -> Meeting:
    return parser_meetings_info(getter_meeting(bakalariAPI, unresolved.ID)).retrieve_type(Meeting)[0]
