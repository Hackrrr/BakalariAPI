# **/next/komens.aspx/GetMessageData**
### Klíč: `komens_get`
# Metadata
| Název                             | Hodnota                    |
|-----------------------------------|:--------------------------:|
| Verze Bakalářů                    | 1.36.1214.1                |
| Datum verze Bakalářů              | 14. 12. 2020               |
| Datum poslední změny dokumentu    | 20. 12. 2020               |
| Potřeba Selenia?                  | Ne                         |

# Přehled
Endpoint normálně nedostupný. Pomocí něj můžeme získat Komens zprávy pomocí ID zprávy.

# Request
Posílá se POST request s ID zprávy a kontextem (viz dále) v JSONu:
```http
POST /next/komens.aspx/GetMessageData HTTP/1.1
{'idmsg':'*ID_ZPRAVY*', 'context':'prijate'}
```
`idmsg` je ID zprávy které chceme získat. `context` indikuje, zda se jedná o přijatou (=> hodnota `prijate`) nebo poslanou/odeslanou zprávu (=> hodnota `odeslane`).

# Response
Pro přijaté zprávy se vrací JSON:
```JSON
{
   "CaptionText":"Obecná zpráva",
   "Cas":"31/12/2020 15:00",
   "Files":[
       ...
   ],
   "Id":"GS15FAAAIE",
   "Jmeno":"ředitesltvi",
   "Kind":"OBECNA",
   "MessageText":"Nějaký text zprávy se span \u003cspan\u003etagem\u003c/span\u003e.",
   "MohuEditovat":false,
   "MohuOdpovedet":false,
   "MohuPotlacit":true,
   "MohuPotvrdit":true,
   "MohuSmazat":false,
   "PoslatNotifikaciOSmazani":true,
   "Potvrzeno":true,
   "PersonChar":"S",
   "PocetFiles":0,
   "CetlJsem":true,
   "PotlacilJsem":false,
   "RatingOfMessage":null,
   "RecipientsDontReadName":[
      "Ing. Břetislav Bakala"
   ],
   "RecipientsReadCount":"potvrzeno: 0 / 1",
   "RecipientsReadName":[

   ],
   "ShowReadCount":false,
   "ShowConfirmButton":true
}
```
Popis klíčů:
- `CaptionText` - Podle názvu klíče bych tipnul "Název zprávy", ale zatím zde byla spatřena pouze jedna hodnota a to `Obecná zpráva` (stejné i v anglické lokalizaci)
- `Files` - Array objektů souborů (viz dále)
- `Cas` - Čas odeslání (/přijetí); Formát je `%d/%m/%Y %H:%M`
- `Id` - ID zprávy
- `Jmeno` - Jméno odesílatele; Pokud je odesílatel `ředitelství`, tak se název mění podle lokalizace (v anglické lokalizaci je to `headmastership`)
- `Kind` - Podle názvu klíče bych tipnul "Typ zprávy", ale zatím zde byla spatřena pouze jedna hodnota a to `OBECNA`
- `MessageText` - Text zprávy; Některé znaky jsou escapované v Unicode (zatím zjištěny tyto znaky: `<`, `>`, `&` a `"`)
- `MohuPotvrdit` - Pokud je hodnota `true`, tak vyžaduje potvrzení
- `PersonChar` - Nevím eShrug . *Asi* indikuje typ odesílatele; Zatím spatřeny hodnoty `S` (zprávy, které odeslalo "ředitelství") a `U` (ostatní zprávy - od učitelů a žáků)
- `RecipientsDontReadName` - Buď `null` anebo array jmen lidí, kteří zprávu ještě nečetli/neviděli; Poznámky viz dále 
- `RecipientsReadCount` - Buď `null` nebo string ve kterém je napsán počet potvrzených zpráv; Poznámky viz dále 
- `RecipientsReadName` - Buď `null` nebo array jmen lidé, kteří již zprávu četli/viděli; Poznámky viz dále


`RecipientsDontReadName`, `RecipientsReadCount` a `RecipientsReadName` jsou *většinou* `null`. Pouze jednou zde byly spatřeny "správné" hodnoty a to u odeslané zprávy (ne přijaté).


Pokud má zpráva přílohu/přílohy, tak klíč `Files` má array objektů souborů. Objekt souboru vypadá následovně:
```JSON
{
    "SizeText":"3 MB",
    "name":"Náhodný soubor.jpg",
    "path":"coekhkhenecpjmffmjkndoopofnejdkffpkkafcmfaeimfjdacidceaeihgjfp.kom",
    "id":"*ID_SOUBORU*",
    "type":"image/jpeg",
    "idmsg":"*ID_ZPRAVY*",
    "Size":2648378
}
```
Vypadá to, že soubor se váže k určité zprávě (klíč `idmsg` se shoduje s ID zprávy). Pro klíč `path` se zatím nenašlo využití.


Pokud zprávu nelze získat (špatné ID, špatný kontext, ...), tak se vrací prázdný objekt:
```JSON
{}
```
Pokud při requestu dosadíme do parametru `context` invalidní hodnotu, tak způsobíme na serveru chybu a vrací se nám [Error JSON](README.md#Error%20JSON).

# Výzkum
Endpoint získán odchytem při zobrazování (přijatých i odeslaných) zpráv. Význam klíčů byl odvozen.
