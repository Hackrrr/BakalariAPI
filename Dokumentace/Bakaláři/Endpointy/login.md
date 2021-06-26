# **/login**
### Klíč: `login`

# Metadata
| Název                             | Hodnota                    |
|-----------------------------------|:--------------------------:|
| Verze Bakalářů                    | 1.36.1214.1                |
| Datum verze Bakalářů              | 14. 12. 2020               |
| Datum poslední změny dokumentu    | 20. 12. 2020               |
| Potřeba Selenia?                  | Ne                         |

# Přehled
Přihlašovací stránka - formulář se jménem a heslem. Přesměrovává sem i request/response na root (tzn. "/") pokud nejsme přihlášeni. Zároveň slouží i pro ověřování údajů přes POST.

# Request
Normální request vypadá takto:
```http
GET /login?ReturnUrl=*PŘESMĚROVÁNÍ* HTTP/1.1
```
Parametr `ReturnUrl`/`returnUrl` není povinný a přímo se reflektuje do parametru `returnUrl` při POST requestu při přihlašování (viz dále).


Pro přihlášení posíláme POST request:
```http
POST /login HTTP/1.1
username=*JMENO*&password=*HESLO*
```
Při "normálním" přihlašování se posílají navíc ještě parametry `returnUrl` a `login` (kvůli logovacímu tlačítku, které je typu `submit`), ale pro přihlášení není potřeba. Parametr `returnUrl` specifikuje kam přesměrovat při přihlášení.

Ještě bych se zastavil u parametru `returnUrl`, především v GET requestu. Tento parametr by se dal považovat za Open Redirect zranitelnost - neprobíhá žádné ověřování, že je adresa je v rámci tohoto serveru/v rámci Bakalářů a ani zda se vůbec jedná o adresu. Není to závažná zranitelnost, ale pořád to lze jako zranitelnost počítat (Open Redirect zranitelnosti se využívají hlavně na phising). Takový jednoduchý PoC je toto:
```
https://bakalari.sps-pi.cz/login?ReturnUrl=https%3a%2f%2fwww%2eyoutube%2ecom%2fwatch%3fv%3ddQw4w9WgXcQ
```
Ano... Uživatelovi může přijít takovýto "dlouhý" link podezřelý a konkrétně u tohoto si třeba i všimne, že se v linku vyskytuje slovo `youtube`. Ale toto je *jen* PoC (teda ne, že by to mohlo být o něco lepší). A pokud vás zajímá, zda se přes toto dá získat login (username i password), tak ne pepeHands - Nejdřív proběhne přihlášení a až přesměrování.

# Response
Vrací se buď HTTP status kód 200 (Ok) při špatném přihlášení a HTML logovací stránky nebo HTTP status kód 302 (Found), tedy přesměrování - přesměruje na [`/dashboard`](dashboard.md) pokud není specifikováno parametrem `returnUrl` jinak.

# Výzkum
Parametry při přihlašování (POST requestu) byly zjištěny odchycením provozu při přihlašování. Parametr `returnUrl` byl zjištěn přes ***skvělé*** automatické odhlašování při neaktivitě, kde se do tohoto parametru předává adresa, na které jsme (byly) neaktivní.
