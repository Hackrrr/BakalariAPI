import logging
from datetime import datetime

LOGGER = logging.getLogger("bakalariapi.modules.homeworks")

from bs4 import BeautifulSoup
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as SeleniumConditions
from selenium.webdriver.support.wait import WebDriverWait

from ..bakalari import BakalariAPI, Endpoint, _register_parser
from ..looting import GetterOutput, ResultSet
from ..objects import Homework, HomeworkFile
from ..sessions import RequestsSession, SeleniumSession


def getter_fast(bakalariAPI: BakalariAPI) -> GetterOutput[BeautifulSoup]:
    """Získá pouze prvních 20 nehotových aktivních úkolů, ale je mnohem rychlejší než ostatní metody na získání úkolů."""
    session = bakalariAPI.session_manager.get_session_or_create(RequestsSession, True)
    response = session.get(bakalariAPI.get_endpoint(Endpoint.HOMEWORKS))
    session.busy = False
    return GetterOutput(
        Endpoint.HOMEWORKS, BeautifulSoup(response.content, "html.parser")
    )


def get_slow(
    bakalariAPI: BakalariAPI,
    unfinished_only: bool = True,
    only_first_page: bool = False,
    first_loading_timeout: float = 5,
    second_loading_timeout: float = 10,
) -> ResultSet:
    """Získá dané domácí úkoly."""

    # TODO: Page size param

    session = bakalariAPI.session_manager.get_session_or_create(SeleniumSession, True)
    session.session.get(bakalariAPI.get_endpoint(Endpoint.HOMEWORKS))
    output = ResultSet()

    if not unfinished_only:
        session.session.find_element_by_xpath(
            "//span[span/input[@id='cphmain_cbUnfinishedHomeworks_S']]"
        ).click()
        # Proč jsem musel šáhnout po XPath? Protože Bakaláři :) Input, podle kterého to můžeme najít, tak je schovaný...
        # A jeho parrent taky... A protože je to schovaný, tak s tím nemůžeme iteragovat... Takže potřebujeme parrenta
        # parrenta toho inputu, který už vidět je a můžeme na něj kliknout :)

    checkID = ""

    while True:
        source = session.session.page_source
        temp_result = parser(
            GetterOutput(Endpoint.HOMEWORKS, BeautifulSoup(source, "html.parser"))
        )

        if temp_result.get(Homework)[0].ID == checkID:
            # Očividně tedy selhalo pozorovnání loading obrazovky a parsujeme stejnou stránku dvakrát, takže cyklus ukončujeme
            # Jen tak mimochodem... toto taky znamená, že Bakaláři jsou zase bugnutý a stránka se neposunula i přesto, že další stránka exististuje
            # (nebo jsme selhali my s detekování existence další stánky, o čemž ale dost pochybuji)
            break

        output.merge(temp_result)

        if not only_first_page:
            try:
                el = session.session.find_element_by_xpath(
                    "//a[@id='grdukoly_DXPagerBottom_PBN']"
                )
            except NoSuchElementException:
                break  # Jsme na poslední stránce
            el.click()
            try:
                WebDriverWait(session.session, first_loading_timeout, 0.1).until(
                    SeleniumConditions.visibility_of_element_located(
                        (By.ID, "grdukoly_LPV")
                    )
                )
            except TimeoutException:
                continue  # Je možný, že načítání bylo rychlejší než náš 0.1 s check na loading screen, takže jdeme rovnou parsovat další stránku
                # tuhle "chybu" kdyžtak zachytíme naším "fail checkem", který případně cyklus ukončí
            try:
                WebDriverWait(session.session, second_loading_timeout).until_not(
                    SeleniumConditions.visibility_of_element_located(
                        (By.ID, "grdukoly_LPV")
                    )
                )
            except TimeoutException:
                LOGGER.info(
                    "Bakaláři probrally stuck in infinity loop while loading homeworks, ending homework getter"
                )
                break  # Pravděpodobně nějaký infinity loading od Bakalářů, se kterým mi nic dělat nemůžeme eShrug
        else:
            break

    session.busy = False
    return output


@_register_parser(Endpoint.HOMEWORKS, BeautifulSoup)
def parser(getter_output: GetterOutput[BeautifulSoup]) -> ResultSet:
    """Parsuje získanou stránku s domácími úkoly a vrací parsované úkoly."""
    output = ResultSet()
    table = getter_output.data.find(id="grdukoly_DXMainTable")
    if table == None:
        # Žádné úkoly (asi) nejsou
        return ResultSet()
    tmp = table.find("tbody")
    if (
        tmp is not None
    ):  # Jelikož to jsou Bakaláři, tak mají 2 rozdílné struktury :); poprvé jsou řádky přímo v <table>, podruhé ještě navíc v <tbody>
        table = tmp
    rows = table("tr", recursive=False)
    for row in rows[1:]:
        # První je hlavička tabulky (normálně bych se divil, proč tu není <thead> a <tbody> (jako u jiných tabulek), ale jsou to Bakaláři, takže to jsem schopnej pochopit)
        tds = row("td")
        datum_odevzdani = datetime.strptime(
            tds[0].find("div")("div")[1].text.strip(), "%d. %m."
        )
        predmet = tds[1].text
        zadani = tds[2].text
        datum_zadani = datetime.strptime(tds[3].text.strip(), "%d. %m.")
        hotovo = tds[5].div.input["value"].lower() == "true"
        ID = tds[6].span["target"]  # = tds[-1]

        files = []
        # if len(tds[4].get_text().strip()) != 0: # Actually nemusíme dělat ani tenhle check a jít rovnou k extrkaci, ale tohle je asi rychlejší
        for a in tds[4]("a"):
            files.append(
                HomeworkFile(a["href"][len("getFile.aspx?f=") :], a.span.text, ID)
            )

        output.add_loot(
            Homework(ID, datum_odevzdani, predmet, zadani, datum_zadani, hotovo, files)
        )
    return output
