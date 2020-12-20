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
Endpoint pro normální úživatele nedostupný. Potvrdí Komens zprávu jako přečtou (pokud vyžaduje přečtení).

# Request
```http
POST /next/komens.aspx/SetMessageConfirmed HTTP/1.1
{'idmsg':'*ID_ZPRÁVY*'}
```
Parametr `idmsg`/`*ID_ZPRÁVY*` je ID zprávy, kterou chceme potvrdit.

# Response
Vrátí se nám JSON:
```JSON
{"d": true}
```
`d` značí *nejspíše* úspěšnost. (zatím netestováno)


TODO: Test this...

# Výzkum
Endpoint a jeho parametr získán odchycením provozu při potvrzování zprávy.