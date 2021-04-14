# **/Collaboration/OnlineMeeting/Detail/**
### Klíč: `meetings_info`

# Metadata
| Název                             | Hodnota                    |
|-----------------------------------|:--------------------------:|
| Verze Bakalářů                    | 1.39.408.1                 |
| Datum verze Bakalářů              | 8. 4. 2021                 |
| Datum poslední změny dokumentu    | 10. 4. 2021                |
| Potřeba Selenia?                  | Ne                         |

# Přehled
Pro normální uživatele nedostupný. Získáme informace o schůzece přes ID schůzky.

# Request
Posíláme GET request na jehož konci je ID schůzky.
```http
GET /Collaboration/OnlineMeeting/Detail/*ID_SCHŮZKY* HTTP/1.1
```

# Response
Vrací se klasicky zabalený JSON:
```JSON
{
   "success":true,
   "error":"",
   "data":{
      "Id":1234,
      "MeetingId":"AQMkADYyZtQxNTFmLWU0NMEtmDYyZi05MmYWLTgyZjQ4NTQyOTg5YQBGAAADw-umPgBqOEi5DCaofeuo1gcAMC8d3HCMpEijse0_agIBP7AAAgENAAAAMC8d3HCMpEijse2_agIBPgAB_e8TBQAAAA==",
      "MeetingStart":"2020-12-31T08:00:00+01:00",
      "MeetingEnd":"2020-12-31T08:45:00+01:00",
      "Title":"Nějaká schůzka třeba prezentace o výborném a skvělém produktu Bakaláři",
      "Details":"Na schůzce se bude prezentovat výborný a skvělý produkt Bakaláři spolu s taktéž skvělým a excelentím produktem Microsoft Teams.",
      "OwnerId":"UMXSV",
      "Error":null,
      "RecipientTypeCode":"ZU",
      "RecipientCode":"1022FC",
      "Participants":[
         ...
      ],
      "ParticipantsReadedCount":10,
      "ParticipantsTotalCount":29,
      "OwnerName":null,
      "ParticipantsListOfRead":[
         ...
      ],
      "ParticipantsListOfDontRead":[
         ...
      ],
      "MeetingStartDate":"2020-12-31T08:00:00+01:00",
      "MeetingStartTime":"2020-12-31T08:00:00+01:00",
      "MeetingEndDate":"2020-12-31T08:45:00+01:00",
      "MeetingEndTime":"2020-12-31T08:45:00+01:00",
      "IsOver":false,
      "IsOwner":false,
      "RecipientsDisplayName":"žáci",
      "CanEdit":false,
      "IsInvitationByEmailOrKomens":true,
      "JoinMeetingUrl":"https://www.youtube.com/watch?v=dQw4w9WgXcQ",
      "HasExternalChange":false,
      "MeetingProviderId": 1
   }
}
```
Popis klíčů (v klíči `data`):
- `Id` - ID schůzky; Narozdíl od ostatních IDček v Bakalařích je toto ID jako číslo a ne jako string
- `MeetingId` - eShrug - Vypadá jako Base64 (a minimálně část je), ale účel nezjištěn
- `MeetingStart` - Začátek schůzky ve formátu `%Y-%m-%dT%H:%M:%S%z`
- `MeetingEnd` - Konec schůzky ve formátu `%Y-%m-%dT%H:%M:%S%z`
- `Title` - Název schůzky
- `Details` - Zpráva schůzky
- `OwnerId` - ID pořadatele
- `Participants` - Obsahuje array objektů jednotlivých účastníků schůzky (resp. pozvaných lidí) (viz dále)
- `OwnerName` - eShrug - Zatím nespatřena jiná hodnota než `null`; Jak získat jméno pořadatele viz poznámka
- `ParticipantsListOfRead` - Obsahuje array objektů jednotlivých účastníků schůzky (resp. pozvaných lidí), kteří již tuto zprávu/pozvánku viděli (viz dále)
- `ParticipantsListOfDontRead` - Obsahuje array objektů jednotlivých účastníků schůzky (resp. pozvaných lidí), kteří již tuto zprávu/pozvánku ještě neviděli (viz dále)
- `MeetingStartDate` - Stejná hodnota jako `MeetingStart`, nechápu, proč to tu je... eShrug
- `MeetingStartTime` - Stejná hodnota jako `MeetingStart`, nechápu, proč to tu je... eShrug
- `MeetingEndDate` - Stejná hodnota jako `MeetingEnd`, nechápu, proč to tu je... eShrug
- `MeetingEndTime` - Stejná hodnota jako `MeetingEnd`, nechápu, proč to tu je... eShrug
- `RecipientsDisplayName` - "Příjemce" (resp. to co se ukazuje jako příjemce)
- `JoinMeetingUrl` - Link/URL na připojení ke schůzce
- `MeetingProviderId` - ID providera schůzky (= platforma schůzky); viz ednpoit `meetings_overview`


Objekty pod klíči `Participants`, `ParticipantsListOfRead` a `ParticipantsListOfDontRead` vypadají takto:
```JSON
{
   "PersonId":"GS12A",
   "PersonName":"Novák Jan C2.E",
   "Readed":"2020-12-31T07:00:00.1234567",
   "RecipientRole":2,
   "Emails":null
}
```
Popis klíčů (v klíči `data`):
- `PersonId` - ID účastníka/pozvaného
- `PersonName` - Jméno účastníka/pozvaného
- `Readed` - Čas, kdy si učastník/pozvaný zprávu přečetl ve formátu `%Y-%m-%dT%H:%M:%S.%f`; To, že poslední čast hodnoty je `%f`, není tak úplně v Pythonu pravda - Zlomek délka zlomku sekundy se může lišit a může přesáhnout délku, kterou `%f` podporuje (6 znaků) (`BakalariAPI` řeší tento problém tím, že zlomky sekundy odsekává) (BTW actually nechápu, proč potřebujeme mít čas přečtení přesnější než microsekundy KEKW )
- `RecipientRole` - Role účastníka/pozvaného na schůzce (asi); `2` = účastníka/pozvaný, `1` = pořadatel/organizátor schůzky
- `Emails` - eShrug - Zatím zde nebyla spatřena jiná hodnota než `null`

*Pozn.: Jelikož klíč `OwnerName` je vždy `null`, tak musíme získat jméno pořadatele/organizátora schůzky jiným způsobem - musíme prohledat array v klíči `Participants` a najít položku, kde její klíč `Id` je shodný s klíčem `OwnerId` v objektu schůzky nebo kde klíč `RecipientRole` je roven `1`.*

Pokud ID schůzky neexistuje, vrátí se HTTP status kód 302 (Found) a přesměrování na `/dashboard` endpointt s prázdným GET parametrem `e`. Pokud ID schůzky existuje, ale schůzka neexistuje (nebo tak něco; takováto schůzka nalezena pouze jednou), vrátí se HTTP status kód 500 (Internal Server Error) a JSON:
```JSON
{
   "success":false,
   "error":"Nepodařilo se načíst detail schůzky.",
   "data":null
}
```

# Výzkum
Endpoint byl získán odchytem při načítání schůzky.