# **/sessioninfo**
### Klíč: `session_info`

# Metadata
| Název                             | Hodnota                    |
|-----------------------------------|:--------------------------:|
| Verze Bakalářů                    | 1.36.1214.1                |
| Datum verze Bakalářů              | 14. 12. 2020               |
| Datum poslední změny dokumentu    | 20. 12. 2020               |
| Potřeba Selenia?                  | Ne                         |

# Přehled
Normálně nedostupný. Pomocí něj se získámá životnost a maximální životnost session. Pokud se jedná o běžného uživatele, tak se v určitém intervalu (jaký je se nezjistilo a je možný, že je dynamický) posílá request na tento endpoint. BTW tenhle endpoint může za vynikající funkci *"Jste tu? Jestli ano, zmáčkmi tlačítko"* a popř. (pokud už session vypršela) zobrazí dialog *"Jste dlouho neaktivní a proto jsme vás z DŮVODU BEZPEČNOSTI odhlásili. (+ tlačíko)"*.

# Request
Normálně (když se o to stará JS na klienstké straně) se posílá GET request s parametrem `_`, který má hodnotu UNIX timestampy uživatele; tento parametr je ale opět k ničemu a opět (znovu a zase) endpoint funguje i bez toho.
```http
GET /sessioninfo HTTP/1.1
``` 

# Response
Vrací se klasicky zabalený JSON:
```JSON
{
   "success":true,
   "error":"",
   "data":{
      "remainingTime":711.1431741,
      "sessionDuration":15.0
   }
}
```
Popis klíčů:
- `remainingTime` - Zbývající životnost současné session v sekundách; Obsahuje i zlomky sekundy na 7 míst
- `sessionDuration` - Maximální životnost session v minutách

Pokud není uživatel přihlášen, `remainingTime` i `sessionDuration` mají hodnotu `0.0` (`success` má pořád hodnotu `true` a `error` je prázdný).

# Výzkum
Endpoint nalezn při odchytu provozu při "neaktivitě".