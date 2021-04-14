# **/Collaboration/OnlineMeeting/MeetingsOverview**
### Klíč: `meetings_overview`

# Metadata
| Název                             | Hodnota                    |
|-----------------------------------|:--------------------------:|
| Verze Bakalářů                    | 1.39.408.1                 |
| Datum verze Bakalářů              | 8. 4. 2021                 |
| Datum poslední změny dokumentu    | 11. 4. 2021                |
| Potřeba Selenia?                  | Ne                         |

# Přehled
Pro normálního uživatele přehled nadcházejících online schůzek. Pro nás zdroj IDček schůzek a to hned dvěma způsoby, které dávají rozdílné věci. Lze získat i něco víc, ale `BakalářiAPI` toho nevyužívá, jelikož data zde jsou nekompletní/neplatné a se znalostí IDčka schůzky lze získat kompletní informace skrze `meetings_info` enpoint.


# Request 0
Já začnu tím "druhým" (druhý znamená, že jsem na něj přišel jako později) protože u prvního máme něco navíc...
Způsob č. 2 je využítí "API", které na to mají. Uděláme POST request na tento endpoint, který vypadá takto:
```http
POST /Collaboration/OnlineMeeting/MeetingsOverview HTTP/1.1
TimeWindow=FromTo&FilterByAuthor=AllInvitations&MeetingFrom=*DATUM_OD*&MeetingTo=*DATUM_DO*
```
Parametry `TimeWindow` a `FilterByAuthor` přeskočím, protože nebyla nalezena cesta jak je užít nějak jinak - prostě je potřebujeme, abychom "aktivovali" tohle "API" a nevrátilo se nám HTML namísto JSONu (který chceme). `MeetingFrom` a `MeetingTo` jsou data na filtraci. Originální formát je `%Y-%m-%dT%H:%M:%S%z`, ale údaj se časového pásma se dá postrádat. Minimum je `0001-01-01T00:00:00` (když za rok dosadí "0000", tak se (podle dat z responsu) převede na `0001`) a maximum `9999-12-31T23:59:59`. 
 
# Response 0
Vrací se klasicky zabalený JSON:
```JSON
{
   "success":true,
   "error":"",
   "data":{
      "Meetings":[
         {
            "Id":*ID_SCHUZKY*,
            "MeetingId":null,
            "MeetingStart":"*START_SCHUZKY*",
            "MeetingEnd":"0001-01-01T00:00:00",
            "Title":"Název schůzky",
            "Details":null,
            "OwnerId":"*ID_POŘADATELE*",
            "Error":null,
            "RecipientTypeCode":null,
            "RecipientCode":null,
            "Participants":null,
            "ParticipantsReadedCount":0,
            "ParticipantsTotalCount":0,
            "OwnerName":"Pořadatel/Vlastník schůzky",
            "ParticipantsListOfRead":null,
            "ParticipantsListOfDontRead":null,
            "MeetingStartDate":"0001-01-01T00:00:00",
            "MeetingStartTime":"0001-01-01T00:00:00",
            "MeetingEndDate":"0001-01-01T00:00:00",
            "MeetingEndTime":"0001-01-01T00:00:00",
            "IsOver":true,
            "IsOwner":false,
            "RecipientsDisplayName":"Nějaký přájemce třeba třída A3",
            "CanEdit":false,
            "IsInvitationByEmailOrKomens":false,
            "JoinMeetingUrl":null,
            "HasExternalChange":false,
            "MeetingProviderId":0
         },
         ...
      ],
      "SelectedMeetingId":null,
      "Filter":{
         "TimeWindow":"FromTo",
         "Directorate":false,
         "Teachers":false,
         "Parents":false,
         "OneClassParents":false,
         "ConcreeteStudentParents":false,
         "ConcreeteStudentParentsCode":null,
         "Students":false,
         "OneClassStudents":false,
         "ConcreeteStudent":false,
         "ConcreeteStudentCode":null,
         "FilterByAuthor":"AllInvitations",
         "MeetingFrom":"0001-01-01T00:00:00",
         "MeetingTo":null,
         "SearchText":null,
         "DisplayDateFrom":"0001-01-01T00:00:00",
         "DisplayDateTo":"0001-01-01T00:00:00"
      },
      "Students":null,
      "IsTeacher":false
   }
}
```
Ano, response je velký... A ano - přes 90% hodnot je neplatných (např. asi tak všechno info o schůzce). Jediné údaje, kterým se dá věřit, tak jsou v klíčích `Id`, `MeetingStart`, `Title`, `OwnerId` a `OwnerName`. Naštěstí chceme tenhle response hlavně kvůli IDčkům schůzek, které můžeme využít u endpointu `meetings_info`. (Pro popis klíčů viz již zmiňovaný endpoint `meetings_info`. Zajímavostí je ale to, že tady je v klíči `OwnerName` validní hotnota.)

# Request 1
Tak to by byl jeden způsob jak získat IDčka schůzek. Druhý způsob je scraping. Posíláme ted GET request:
```http
GET /Collaboration/OnlineMeeting/MeetingsOverview HTTP/1.1
```

# Response 1
Vrátí se nám HTML, které musíme scrapenout.

## Extrakce dat 0 - HTML => JS => JSON
Sice je to náročnější scrapping, ale taky z toho můžeme získat o dost více informací. Zde totiž musíme scrapnout JS ze `<script>` tagu. Navíc tento `<script>` není nijak označen a to znamená, že buď budeme spoléhat že to bude třeba 3. tag od konce a nebo ho musíme celý prohledat a podívat se, jestli to není ten, který hledáme. `BakalářiAPI` hledá daný `<script>` tag druhým způsobem, tedy bruteforcem - projde všechny `<script>` tagy v `<head>` tagu a pokud najde v JS tohoto tagu string `var model = `, tak považuje tento tag za správný. Dál projíždí celý JS tohoto tagu a hledá řádku, která (, když se osekají mezery a taby,) začíná stringem `var meetingsData = `. Pokud takovou řádku najde, tak tento začátek odsekne a zbyde jen JSON array schůzek (a středník na konci) (actually tady to není JSON jako JSON - tady je to prostě definice objektů v JS). JSON vypadá takto:
```JSON
[
    {
        "Id":*ID_SCHUZKY*,
        "MeetingId":null,
        "MeetingStart":"*START_SCHUZKY*",
        "MeetingEnd":"0001-01-01T00:00:00",
        "Title":"Název schůzky",
        "Details":null,
        "OwnerId":"*ID_POŘADATELE*",
        "Error":null,
        "RecipientTypeCode":null,
        "RecipientCode":null,
        "Participants":null,
        "ParticipantsReadedCount":0,
        "ParticipantsTotalCount":0,
        "OwnerName":"Pořadatel/Vlastník schůzky",
        "ParticipantsListOfRead":null,
        "ParticipantsListOfDontRead":null,
        "MeetingStartDate":"0001-01-01T00:00:00",
        "MeetingStartTime":"0001-01-01T00:00:00",
        "MeetingEndDate":"0001-01-01T00:00:00",
        "MeetingEndTime":"0001-01-01T00:00:00",
        "IsOver":true,
        "IsOwner":false,
        "RecipientsDisplayName":"Nějaký přájemce třeba třída A3",
        "CanEdit":false,
        "IsInvitationByEmailOrKomens":false,
        "JoinMeetingUrl":null,
        "HasExternalChange":false,
        "MeetingProviderId":0
    },
    ...
]
```
Údaje o schůzkách jsou stejně kvalitní jako u předchozího způsobu, tedy že 90% jsou invalidní/neplatná data. Ale máme IDčka schůzek (ale jen nadcházejících).


## Extrakce dat 1 - HTML => JS => JSON
No ale proč to dělat touto metodou? Vždyť tohle je úplně k ničemu, když máme jiný a lepší způsob... No - v tomto `<script>` tagu se nachází ještě seznam všech studentů na škole... Ano... **A absolutně nemám ponětí, co tam dělá, jelikož jsem nenarazil na jedinou věc, kde se používá...** Možná by se to mělo někomu nahlásit, ale já jsem línej to dělat. Každopádně nyní hledáme řádku začínající (opět po osekání mezer a tabů) `model.Students = ko.mapping.fromJS(`. Když ji najdeme a osekneme začátek a konec (tedy `");"`), tak získáme JSON studentů:
```JSON
[
    {
      "Id":"*ID_STUDENTA*",
      "Name":"*JMÉNO*",
      "Surname":"*PŘÍJMENÍ*",
      "Class":"*TŘÍDA*",
      "FullName":"*TŘÍDA* *JMÉNO* *PŘÍJMENÍ*"
   },
   ...
]
```
Klíč `"Name"` popřípadě obsahuje i druhé jméno. Klíč `FullName` je poskládán z ostatních hodnot.


# MeetingsProvider
Verzi Bakalářů `1.37.*` přibyl v JSON datech na endpointech `meetings_overview` a `meetings_info` klíč `MeetingProviderId`. Tento klíč pravděpodobně indikuje platformu/providera schůzky, avšak zatím nebyla zaznamenána jiná hodnota než `1`.

| ID  | Klíč            | Popisek                                 |
|:---:|-----------------|-----------------------------------------|
| 0   | None            | žádný                                   |
| 1   | Microsoft       | Microsoft Office 365 for Education      |
| 2   | Google          | Google Meet                             |

*Pozn.: Ačkoli na endpointu `meetings_overview` má klíč `MeetingProviderId` vždy hodnotu `0`, je tato tablka zde, jelikož data, z nichž tato tabulka vychází, jsou na tomto endpointu.*

Ačkoli by se tato data dala považovat za dynamická, jelikož jsou v Bakalářích "dynamicky" dosazana skrze JS, pochybuji, že by se tato tabulka/tyto data nějak často měnily nebo byly odlišné v jednotlivých instancích Bakalářů. `BakalářiAPI` má v tuto chvíli tyto data "uložena" staticky, ale uvažuje se o jejich dynamickém získávání. Z toho důvodu se zde uvádí i daný `<script>` tag, ve kterém jsou v Bakalářích tyto data incializována (tento tag předchází tagu, kde jsou uložena data na schůzky i o studentech):
```html
<script type='text/javascript'>
   var Dictionaries = [];
   Dictionaries['MeetingProvider'] = [];
   Dictionaries['MeetingProvider']['_Google']={"id":2,"key":"Google","label":"Google Meet"}; 
   Dictionaries['MeetingProvider'].push(Dictionaries['MeetingProvider']['_Google']); 
   Dictionaries['MeetingProvider']['_Microsoft']={"id":1,"key":"Microsoft","label":"Microsoft Office 365 for Education"}; 
   Dictionaries['MeetingProvider'].push(Dictionaries['MeetingProvider']['_Microsoft']); 
   Dictionaries['MeetingProvider']['_None']={"id":0,"key":"None","label":"žádný"}; 
   Dictionaries['MeetingProvider'].push(Dictionaries['MeetingProvider']['_None']); 
   Object.freeze(Dictionaries);
</script>
```

# Výzkum
Enpoint nalezen přes normální proklik přes menu. "Request 0" byl zjištěn přes odchyt výsledků filtrování a následně vyzkoušeno, které parametry je potřeba a které lze vyhodit. Co znamenají jaká data v "Response 0" bylo odvozeno. Možnost získání dat z JS byla objevena při manuální průzkumu zdroje při hledání způsobu, jak scrapnout schůzky.

Data do tabulky MeetigsProvider byla získána analýzou zdrojového kódu, při výskytu nového pole v uživatelském rozhraní Bakalářů.