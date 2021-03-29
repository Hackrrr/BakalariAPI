import json
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from ..bakalari import BakalariAPI, Endpoint, RequestsSession, bakalariextension


@bakalariextension
def is_server_running(bakalariAPI: BakalariAPI) -> bool:
    try:
        response = requests.get(bakalariAPI.url)
        response.raise_for_status()
    except requests.exceptions.RequestException:
        return False
    return True

@bakalariextension
def is_login_valid(bakalariAPI: BakalariAPI) -> bool:
    session = bakalariAPI.session_manager.get_session_or_create(RequestsSession)
    output = session.login()
    if not output:
        session.kill()
        bakalariAPI.session_manager.unregister_session(session)
    else:
        session.busy = False
    return output

@bakalariextension
def init(bakalariAPI: BakalariAPI):
    session = bakalariAPI.session_manager.get_session_or_create(RequestsSession)
    data = json.loads(BeautifulSoup(session.get(bakalariAPI.get_endpoint(Endpoint.USER_INFO)).content, "html.parser").head["data-pageinfo"])
    bakalariAPI.user_info.type = data["userType"]
    bakalariAPI.user_info.hash = data["userHash"]
    bakalariAPI.server_info.version = data["applicationVersion"]
    bakalariAPI.server_info.version_date = datetime.strptime(data["appVersion"], "%Y%m%d")
    bakalariAPI.server_info.evid_number = int(data["evidNumber"])
    session.busy = False

@bakalariextension
def get_my_ID(bakalariAPI: BakalariAPI) -> str:
    #TODO: This
    #bakalariAPI.UserInfo.ID = ...
    pass
