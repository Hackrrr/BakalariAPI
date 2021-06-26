# **/next/komens.aspx/SetMessageConfirmed**
### Klíč: `komens_confirm`

# Metadata
| Název                             | Hodnota                    |
|-----------------------------------|:--------------------------:|
| Verze Bakalářů                    | 1.36.1214.1                |
| Datum verze Bakalářů              | 14. 12. 2020               |
| Datum poslední změny dokumentu    | 20. 12. 2020               |
| Potřeba Selenia?                  | Ne                         |

# Přehled
Endpoint pro normální uživatele nedostupný. Potvrdí Komens zprávu jako přečtou (pokud vyžaduje přečtení).

# Request
```http
POST /next/komens.aspx/SetMessageConfirmed HTTP/1.1
{'idmsg':'*ID_ZPRÁVY*'}
```
"Parametr" `idmsg`/`*ID_ZPRÁVY*` je ID zprávy, kterou chceme potvrdit.

# Response
Vrátí se nám JSON:
```JSON
{"d": true}
```
`d` značí *nejspíše* úspěšnost "vykonání". Ve většině případů bude `true`, nehledě na (ne)existenci daného ID. Jediný případ, kdy se zde objevila hodnota `false`, bylo, když parametr `idmsg` byl nastaven na `null`.

Pokud klíč `idmsg` v zaslaném objektu chybí, tedy když pošleme prázdný objekt `{}` nebo prázdný body request, vrátí se [Error JSON](README.md#Error%20JSON).

# Výzkum
Endpoint a jeho parametr získán odchycením provozu při potvrzování zprávy. Chování endpointu bylo dále zjištěno testováním.