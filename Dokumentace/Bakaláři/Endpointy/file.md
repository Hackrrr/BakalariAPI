# **/next/getFile.aspx**
### Klíč: `file`

# Metadata
| Název                             | Hodnota                    |
|-----------------------------------|:--------------------------:|
| Verze Bakalářů                    | 1.36.1214.1                |
| Datum verze Bakalářů              | 14. 12. 2020               |
| Datum poslední změny dokumentu    | 20. 12. 2020               |
| Potřeba Selenia?                  | Ne                         |

# Přehled
Pro normální uživatele nedostupný. Slouží ke stahování souborů s určitím ID. Posílá se GET request s parametrem `f` jehož hodnota je ID souboru, kteerý chceme stáhnout.

# Request
```http
GET /next/getFile.aspx?f=*ID_SOUBORU* HTTP/1.1
```
`*ID_SOUBORU*` je ID souboru, který chceme stáhnout/získat.

# Response
Pokud je ID souboru validní, tak začne stahování. Pokud ne, tak se vrátí následující HTML (HTTP status kód je 200 (OK)):
```html
<!DOCTYPE html>

<html>
<head>
    <meta name="viewport" content="width=device-width" />
    <title>Soubor nenalezen</title>
</head>
<body>
    <div> 
        Požadovaný soubor neexistuje.
    </div>
</body>
</html>
```

# Výzkum
Endpoint byl (původně) získán skrz link u/při stahování příloh u komens zpráv.