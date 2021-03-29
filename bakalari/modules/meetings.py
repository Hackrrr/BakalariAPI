import json
from datetime import datetime

from bs4 import BeautifulSoup

from ..bakalari import BakalariAPI, Endpoint, RequestsSession, bakalariextension, bakalarilootable_extension
from ..utils import line_iterator
from ..bakalariobjects import Meeting, Student


@bakalarilootable_extension
def get_meeting(bakalariAPI: BakalariAPI, ID: str) -> Meeting:
    """Získá schůzku s daným ID."""
    session = bakalariAPI.session_manager.get_session_or_create(RequestsSession, True)
    response = session.get(bakalariAPI.get_endpoint(Endpoint.MEETINGS_INFO) + ID).json()
    session.busy = False
    meeting = Meeting(
        response["data"]["Id"],
        response["data"]["OwnerId"],
        response["data"]["Title"],
        response["data"]["Details"],
        datetime.strptime(response["data"]["MeetingStart"], "%Y-%m-%dT%H:%M:%S%z"),
        datetime.strptime(response["data"]["MeetingEnd"], "%Y-%m-%dT%H:%M:%S%z"),
        response["data"]["JoinMeetingUrl"],
        [(s["PersonId"], s["PersonName"]) for s in response["data"]["Participants"]],
        [(s["PersonId"], datetime.strptime(s["Readed"][:-(len(s["Readed"]) - s["Readed"].rfind("."))], "%Y-%m-%dT%H:%M:%S")) for s in response["data"]["ParticipantsListOfRead"]]
    )
    return meeting

@bakalariextension
def get_future_meetings_IDs(bakalariAPI: BakalariAPI) -> list[str]:
    """Získá IDčka budoucích schůzek."""
    session = bakalariAPI.session_manager.get_session_or_create(RequestsSession, True)
    response = session.get(bakalariAPI.get_endpoint(Endpoint.MEETINGS_OVERVIEW))
    session.busy = False

    soup = BeautifulSoup(response.content, "html.parser")
    output = []
    scritps = soup.head("script")
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
                output.append(str(meeting["Id"])) # Actually je to číslo, ale všechny ostaní IDčka jsou string, takže se budeme tvářit že je string i tohle...
        elif line.startswith("model.Students = ko.mapping.fromJS("):
            loot["Students"] = True
            studentsJSON = json.loads(line.strip()[len("model.Students = ko.mapping.fromJS("):-2])
            for student in studentsJSON:
                bakalariAPI.looting.add_loot(Student(
                    student["Id"],
                    student["Name"],
                    student["Surname"],
                    student["Class"]
                ))
        if loot["Meetings"] and loot["Students"]:
            break
    return output

@bakalariextension
def get_meetings_IDs(bakalariAPI: BakalariAPI, from_date: datetime, to_date: datetime) -> list[str]:
    """Získá IDčka daných nebo všech schůzek."""
    session = bakalariAPI.session_manager.get_session_or_create(RequestsSession, True)
    response = session.post(bakalariAPI.get_endpoint(Endpoint.MEETINGS_OVERVIEW), {
        "TimeWindow": "FromTo",
        "FilterByAuthor": "AllInvitations",
        "MeetingFrom": from_date.strftime("%Y-%m-%dT%H:%M:%S") + "+00:00",
        "MeetingTo": to_date.strftime("%Y-%m-%dT%H:%M:%S") + "+00:00"
    }).json()
    session.busy = False
    output = []
    for meeting in response["data"]["Meetings"]:
        output.append(str(meeting["Id"]))
    return output

@bakalariextension
def get_all_meetings_IDs(bakalariAPI: BakalariAPI) -> list[str]:
    """Získá IDčka všech schůzek"""
    return bakalariAPI.get_meetings_IDs(datetime(1, 1, 1), datetime(9999, 12, 31, 23, 59, 59))
