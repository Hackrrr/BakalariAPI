"""
Jednoduché (i složitější) utility sloužící ke správnému fungování BakalářiAPI.
"""

from datetime import datetime

from bs4 import BeautifulSoup


def first2upper(string: str) -> str:
    """První znak ve stringu dá do Uppercase"""
    return string[0].upper() + string[1:]


def string2datetime(string: str) -> datetime:
    """Pokusí se získat převést string na datum dle předdefinovaných formátů. Pokud neuspěje, vyhodí ValueError."""
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S%z",
        "%Y-%m-%d %H:%M:%ST%z",
        "%Y-%m-%d"
    ]
    for date_format in formats:
        try:
            return datetime.strptime(string, date_format)
        except ValueError:
            pass
    raise ValueError

def line_iterator(text: str):
    """Slouží jako iterátor řádek pro text. (Vypůjčeno (resp. ukradeno) ze Stacku.)"""
    prevnl = -1
    while True:
        nextnl = text.find('\n', prevnl + 1)
        if nextnl < 0:
            break
        yield text[prevnl + 1:nextnl]
        prevnl = nextnl

def bs_get_text(soup: BeautifulSoup) -> str:
    """BeautifulSoup.get_text(), ale tak trochu jinak
    BeautifulSoup dělá vynikající práci... Ale na prasárny Bakalářů to ani tak nestačí
    To co tohle udělá a '.get_text()' ne:
        - Nahradí "<br/>" za \n... '.get_text()' zvládá jen syntakticky správně (tedy "<br />" nebo jen "<br>")
        - Pokud je zde "<body>" tag, tak vezme jen ten
        - Stripne text (Je to vůbec potřeba? eShrug)
    """

    #TODO: Převést <p> na nové řádky
    for br in soup("br"):
        br.replace_with("\n" + br.text)

    body = soup.find("body")
    if body != None:
        soup = body

    return soup.get_text().strip()
