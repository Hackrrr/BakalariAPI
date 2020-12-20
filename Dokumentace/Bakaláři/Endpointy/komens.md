# **/next/komens.aspx**
### Klíč: `komens`
*(Ano, je to **prubzna**, není to překlep (tedy nejspíš je, ale ne můj)...)*

# Metadata
| Název                             | Hodnota                    |
|-----------------------------------|:--------------------------:|
| Verze Bakalářů                    | 1.36.1214.1                |
| Datum verze Bakalářů              | 14. 12. 2020               |
| Datum poslední změny dokumentu    | 20. 12. 2020               |
| Potřeba Selenia?                  | Ne                         |

# Přehled
Pro normálního uživatele stránka pro zobrazení Komens zpráv. Pro nás zdroj IDček jednotlivých zpráv. Lze získat i něco víc, ale `BakalariAPI` toho nevyužívá, jelikož data zde jsou nekompletní a se znalostí IDčka zprávy lze získat kompletní informace skrze `komens_get` enpoint.

# Request
```http
GET /next/komens.aspx?s=custom&from=*DATUM_OD*&to=*DATUM_DO* HTTP/1.1
```
Popřípadě:
```http
GET /next/komens.aspx?s=custom&from=*DATUM_OD*&to=*DATUM_DO*&l=o HTTP/1.1
```
Tyto requesty se liší pouze v přidání parametru `l` s hodnoutou `o` (lze použít i hodnotu `odeslane`). Pokud je takovýto parametr přítomen, vratí se nám seznam odeslaných zpráv a ne přijatých. Request lze poslat i bez parametrů (tedy bez filtrace) a vratí se seznam přiajtých Komens zpráv z tohoto pololetí.


Datum v parametrech `from` a `to` je ve formátu `%d%m%Y`. Nejmenší hodnota, co se do nich může dosadit je 1. 1. 1753, tedy `01011753`. Pravděpodobně běží na starém SQL serveru (nebo používají starý věci, který používat nemají), který nepodporuje dřívější datum kvůli "chybějícím" dnům. Ref: [https://stackoverflow.com](https://stackoverflow.com/questions/3310569/what-is-the-significance-of-1-1-1753-in-sql-server)

# Response
Vrací se HTML.

## Extrakce dat - HTML => ID zpráv
Zajímá nás `<div>` jehož `id` je `message_list_content`. V něm je list, jehož položky obsahují ID zprávy v atributu `data-idmsg`. HTML zjednodušeně vypadá nějak takto:
```html
<div ... id="message_list_content" ...>
    <ul>
        <li>
            <table ... data-idmsg="*ID_ZPRAVY*" ...> ... </table>
        </li>
        <li>
            <table ... data-idmsg="*ID_ZPRAVY*" ...> ... </table>
        </li>
        <li>
            <table ... data-idmsg="*ID_ZPRAVY*" ...> ... </table>
        </li>
        ...
    </ul>
</div>
```

# Výzkum
Při hlednání způsobu, jak parsovat zprávy byla v HTML, při manuálním prohledáváním zdroje stránky, nalezany IDčka zpráv. To že se jedná o IDčka zpráv bylo odvozeno ve spojitosti s poznatky o endpoitu `komens_get`.