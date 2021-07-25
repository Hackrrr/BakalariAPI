"""Soubor vyjímek, které mohou nastat v BakalářiAPI."""

# Prefix "BakalariAPI" u výjimek je pouze u "základních" (`BakalariAPIException`, `BakalariAPIError`
# a `BakalariAPIWarning`). U ostatních tento prefix není nutný, aby neznikali neprakticky dlouhé názvy.

### BASE ###
class BakalariAPIException(Exception):
    """Základní výjimka pro BakalářiAPI, ze kterého derivují všechny ostatní."""


class BakalariAPIError(BakalariAPIException):
    """Základní error výjimka pro BakalářiAPI, ze kterého derivují všechny ostatní error výjimky."""


class BakalariAPIWarning(BakalariAPIException, UserWarning):
    """Základní warning výjimka pro BakalářiAPI, ze kterého derivují všechny ostatní warrning výjimky."""


### ERROR ###
class BakalariQuerrySuccessError(BakalariAPIError):
    """Výjimka, která nastane, když u některých dotazů, které vrací JSON, je klíč "success" nastaven na `false`."""


class MissingSeleniumHandlerError(BakalariAPIError):
    """Výjimka, která nastane při pokusu o Selenium featuru, když není dostupná SeleniumHandler instance."""

class MissingElementError(BakalariAPIError):
    """Výjimka, která nastane při chybějícím elementu jak v HTML, tak v JSON datech.
    
    Tato výjimka by měla nastat pouze v případě, kdy verze Bakalářů je jiná, než `LAST_SUPPORTED_VERSION`.
    Pokud výjimka nastane i v jiném případě (tedy když se verze shodují), jde o bug v `BakalářiAPI`.
    """

### WARNING ###
class VersionMismatchWarning(BakalariAPIWarning):
    """Výjimka, která nastane při neshodě verze Bakalářů a `LAST_SUPPORTED_VERSION`.
    
    Tento warning se může ignorovat, jelikož ve většině případů se nic závažného neděje.
    Je poteřeba mít na paměti, že pokud tento warning nastane, `BakalářiAPI` může být nestabilní.
    """