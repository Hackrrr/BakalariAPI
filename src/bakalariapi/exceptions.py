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


class PartialInitError(BakalariAPIError):
    """Výjimka, která může nastat při určitých akcích, pokud `BakalariAPI` instance nebyla plně inicializována.

    Tato výjimka by měla nastat pouze v případě, kdy `BakalariAPI.is_partial_init` je `True`.
    Pokud výjimka nastane v přápadě, kdy  `BakalariAPI.is_partial_init` je `False`, jde o bug v `BakalářiAPI`.
    """


class MissingSerializer(BakalariAPIError):
    """Výjimka, která nastane při pokusu o serilializaci typu, který nelze serializovat přes `serializable.Serializable` protokol nebo přes registrované serializery.

    Pozn.: Přestože nastane tato výjimka, typ může být stále serializovatelný.
    Např. tato výjimka nastane pro typ `int`, jelikož samotný typ neimplementuje `Serializable` protokol a (pravděpodobně)
    pro něj nebude zaregistrován žádný serializer, avšak základní JSON serializer je schopný `int` serializovat.
    """


class MissingDeserializer(BakalariAPIWarning):
    """Výjimka, která nastane při pokusu o deserilializaci dat, které vypadají, že by se dali deserializovat, ale není pro ně registrovaný deserializer."""


### WARNING ###
class VersionMismatchWarning(BakalariAPIWarning):
    """Varování, které nastane při neshodě verze Bakalářů a `LAST_SUPPORTED_VERSION`.

    Toto varování se může ignorovat, jelikož ve většině případů se nic závažného neděje avšak `BakalářiAPI` může být nestabilní.
    """
