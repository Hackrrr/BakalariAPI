class Exception(Exception):
    """Základní exception classa pro BakalariAPI
    Všechny výjimky mají dědičnou cestu k této výjimky"""


class AuthenticationException(Exception):
    """Výjimka při autentizaci"""

class ConnectionException(Exception):
    """Výjimka při chybě při pokusu o připojení - Server nebo Bakaláři pravděpodobně neběží"""

class InputException(Exception):
    """Výjimka při chybném vstupu"""
    
class UserNotLoggedIn(Exception):
    """Výjimka při pokusu o vykonání autentizované akci, když uživatel není přihlášen"""


class Warning(UserWarning):
     """Základní warning classa pro BakalariAPI
    Všechny varování mají dědičnou cestu k tomuto varování"""


class UnexpectedBehaviour(Warning):
    """Nečekaná odpoveď/přesměrování od serveru (pravděpodobně na serveru běží jiná (nová) veze Bakalařů)"""

class DifferentVersion(Warning):
    """Bakaláři mají jinou verzi, než BakalariAPI podporuje"""

class SameID(Warning):
    """Nalezeny objekty, které mají stejné ID ale nejsou totožný
    Pozn.: Mohou být i totžný, ale """