"""Modul obsahující funkce týkající se úkolů."""
import logging
from datetime import datetime
from typing import cast

from bs4 import BeautifulSoup
from bs4.element import Tag  # Kvůli mypy - https://github.com/python/mypy/issues/10826
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as SeleniumConditions
from selenium.webdriver.support.wait import WebDriverWait

from ..bakalari import BakalariAPI, Endpoint, _register_parser
from ..exceptions import MissingElementError
from ..looting import GetterOutput, ResultSet
from ..objects import Homework, HomeworkFile
from ..sessions import RequestsSession, SeleniumSession
from ..utils import parseHTML

LOGGER = logging.getLogger("bakalariapi.modules.homeworks")


def getter_fast(bakalariAPI: BakalariAPI) -> GetterOutput[BeautifulSoup]:
    """Získá pouze prvních 20 nehotových aktivních úkolů, ale je mnohem rychlejší než ostatní metody na získání úkolů."""
    with bakalariAPI.session_manager.get_session_or_create(RequestsSession) as session:
        response = session.get(bakalariAPI.get_endpoint(Endpoint.HOMEWORKS))
    return GetterOutput(Endpoint.HOMEWORKS, parseHTML(response.content))


def get_slow(
    bakalariAPI: BakalariAPI,
    unfinished_only: bool = True,
    only_first_page: bool = False,
    first_loading_timeout: float = 5,
    second_loading_timeout: float = 10,
) -> ResultSet:
    """Získá dané domácí úkoly."""

    # TODO: Page size param

    with bakalariAPI.session_manager.get_session_or_create(SeleniumSession) as session:
        session.session.get(bakalariAPI.get_endpoint(Endpoint.HOMEWORKS))
        output = ResultSet()

        if not unfinished_only:
            session.session.find_element_by_xpath(
                "//span[span/input[@id='cphmain_cbUnfinishedHomeworks_S']]"
            ).click()
            # Proč jsem musel šáhnout po XPath? Protože Bakaláři :) Input, podle kterého to můžeme najít, tak je schovaný...
            # A jeho parent taky... A protože je to schovaný, tak s tím nemůžeme iteragovat... Takže potřebujeme parenta
            # parenta toho inputu, který už vidět je a můžeme na něj kliknout. Prostě super :)

        checkID = ""

        while True:
            source = session.session.page_source
            temp_result = bakalariAPI._parse(
                GetterOutput(Endpoint.HOMEWORKS, parseHTML(source))
            )

            if temp_result.get(Homework)[0].ID == checkID:  # Náš "fail check"
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
                    # Je možný, že načítání bylo rychlejší než náš 0.1 s check na loading screen, takže jdeme rovnou parsovat další stránku
                    # Tuto "chybu" kdyžtak zachytíme naším "fail checkem", který případně cyklus ukončí
                    continue
                try:
                    WebDriverWait(session.session, second_loading_timeout).until_not(
                        SeleniumConditions.visibility_of_element_located(
                            (By.ID, "grdukoly_LPV")
                        )
                    )
                except TimeoutException:
                    LOGGER.info(
                        "Probrally stuck in infinity loop while loading homeworks, ending homework getter"
                    )
                    break  # Pravděpodobně nějaký infinity loading od Bakalářů, se kterým mi nic dělat nemůžeme eShrug
            else:
                break
    return output


@_register_parser(Endpoint.HOMEWORKS, BeautifulSoup)
def parser(getter_output: GetterOutput[BeautifulSoup]) -> ResultSet:
    """Parsuje získanou stránku s domácími úkoly a vrací parsované úkoly."""
    output = ResultSet()
    table = cast(Tag, getter_output.data.find(id="grdukoly_DXMainTable"))
    if table is None:
        # Žádné úkoly (asi) nejsou
        return ResultSet()
    tmp = cast(Tag, table.find("tbody"))
    # Jelikož to jsou Bakaláři, tak mají 2 rozdílné struktury :) Poprvé jsou řádky přímo v <table>, podruhé jsou vnořeny ještě v <tbody>
    if tmp is not None:
        table = tmp
    rows = cast(list[Tag], table("tr", recursive=False))
    for row in rows[1:]:  # První řádek je hlavička tabulky, takže přeskakujeme
        # Ok, tohle je špatný a ano, vím to... Ale TBH, pokud se něco pokazí, tak se stejně bude debugovat
        # více do podrobna, takže informace kde přesně v "řetězu" je chyba až tak podstatná není
        # Ignore `tds` => `tds` je Unknown => Pylance si nestěžuje na dalších řádkách
        # Pokud bychom správně napověděli přes `cast()`, že `tds` je `list[Tag]`, tak pak si Pylance stěžuje mnohem více
        # a museli bychom doslova na každý řádek cpát další `cast()` (někde i vícekrát na jeden řádek)
        try:
            tds = cast(list[Tag], row("td"))
            datum_odevzdani = datetime.strptime(
                cast(list[Tag], cast(Tag, tds[0].find("div"))("div"))[1].text.strip(),
                "%d. %m.",
            )
            predmet = tds[1].text
            zadani = tds[2].text
            datum_zadani = datetime.strptime(tds[3].text.strip(), "%d. %m.")
            # Aby se nemuseli dělat `None` checky, tak se jen chytí případný `AttributeError`
            try:
                hotovo = tds[5].div.input["value"].lower() == "true"  # type: ignore
            except AttributeError as e:
                raise MissingElementError from e
            try:
                ID = cast(str, tds[6].span["target"])  # type: ignore
            except AttributeError as e:
                raise MissingElementError from e

            try:
                files = [
                    HomeworkFile(a["href"][len("getFile.aspx?f=") :], a.span.text, ID)  # type: ignore
                    for a in cast(list[Tag], tds[4]("a"))
                ]
            except AttributeError as e:
                raise MissingElementError from e
            output.add_loot(
                Homework(
                    ID, datum_odevzdani, predmet, zadani, datum_zadani, hotovo, files
                )
            )
        except (TypeError, AttributeError):
            raise MissingElementError()
    return output
