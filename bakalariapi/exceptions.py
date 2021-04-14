"""Soubor vyjímek, které mohou nastat v BakalářiAPI."""


class BakalariAPIException(Exception):
    """Základní Exception pro BakalářiAPI, ze kterého derivují všechny ostatní."""

class NoSeleniumException(BakalariAPIException):
    """Exception, která nastane při pokusu o akci vyžadující Selenium přicemž ale Selenium není nainstalováno."""
