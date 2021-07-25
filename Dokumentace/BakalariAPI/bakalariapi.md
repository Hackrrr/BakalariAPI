# Začátek
Celý `BakalářiAPI` se točí kolem třídy `bakalari.BakalariAPI`:
```py
from bakalari import BakalariAPI
api = BakalariAPI("https://bakalari.mojeskola.cz", "MojeSkvěléJméno", "MojeSuperTajnéHeslo")
if api.is_server_running() and api.is_login_valid():
    api.init()
else:
    raise Exception("Něco se pokazilo... Sadge")
```
A voilà! Je hotovo! Počkat co? Takhle ti to nestačí? Tak jdu napsat dokumentaci ještě pro jednotlivé funkce...

# Metody
Metody třídy `BakalariAPI`