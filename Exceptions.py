class Vyjimka(Exception):
    """Základní exception classa pro BakalariAPI
    Všechny výjimky mají dědičnou cestu k této výjimky"""


class ChybaAutentizace(Vyjimka):
    """Authentization error"""

class ChybaPripojeni(Vyjimka):
    """Sever/web exception, when service is unavalible"""

class ChybaVstupu(Vyjimka):
    """Invalid input exception"""



class Varovani(UserWarning):
     """Základní warning classa pro BakalariAPI
    Všechny varování mají dědičnou cestu k tomuto varování"""


class NecekaneChovani(Varovani):
    """Nečekaná odpoveď/přesměrování od serveru (pravděpodobně na serveru běží jiná (nová) veze Bakalařů)"""