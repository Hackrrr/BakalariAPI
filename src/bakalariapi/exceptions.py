"""Soubor vyjímek, které mohou nastat v BakalářiAPI."""


class BakalariAPIException(Exception):
    """Základní exception pro BakalářiAPI, ze kterého derivují všechny ostatní."""


class BakalariAPIError(Exception):
    """Základní error exception pro BakalářiAPI, ze kterého derivují všechny ostatní errory."""

class BakalariQuerrySuccessError(BakalariAPIError):
    """Exception, která nastane, když u některých dotazů, které vrací JSON, je klíč "success" nastaven na false."""
