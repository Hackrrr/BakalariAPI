# Poznámky
Tohle je souboru s poznatkama o Bakalářích, jak fungujou a co kdy dělají...
Nejedná se tedy o dokumentaci k `BakalariAPI`, ale spíše jedná se spíše o poznámky, které by mohli pomoc další magorům, co se budou pokoušet o stejnou věc... :)<br>
Pro vytažení dat z HTML používajá `BakalariAPI` modul `BeautifulSoup4` (zkráceně `bs4`) ([link zde](https://www.crummy.com/software/BeautifulSoup/)) a příklady jeho využití zde nejsou... Pokud ale hledáte tutoriál k `bs4`, tak bych doporučil [toto](https://realpython.com/beautiful-soup-web-scraper-python/).
# Moje vyjádření k Bakalářům
Za tu dobu, co se vrtám v IT jsem toho viděl už relativně dost. A zcela určitě můžu prohlásit, že Bakaláři je snad to nejhorší co jsem viděl... Jen se podívejte na to, co za prasárny se tam děje... Vypadá to jak kdyby to dělalo 30 lidí, každý měl jinou představu, jak by to mělo fungovat a tak to udělal každý po svém. 80% věcí je dělaných jedním způsobem, dalších 75% jiným, následujících 60% je něco mezitím a těch zbylích 30% je každý nějak jinak. Nehledě na to, že referencujou snad všechny knihovny, co našli... Jediný co se dá na Bakalářích pochválit je design (což je actually asi jedniná věc o kterou se koncový uživatel stará). Ok, dokážu přehlédnout neexistenci "normálního" API - třeba to chtěli udělat těžší pro ty, co to budou revesovat (a stejně tu jsou určitý věci přes API)... Ale prostě... Dám příklad úkolů (což je asi největší prasárna ze všech):<br>
Pomineme první načtení (na to nemám nervy rozepisovat)... Když chcete změnit velikost stránky, tak se pošle request s doslova víc jak 10ti hodnotama, znichž většina z jich jsou doslova statická data, vrátí se JSON, který má v sobě HTML, které se vloží na stránku a toto HTML spustí JS (protože má v sobě asi 6 `<script>` tagů), které vezmou to HTML, přetransformujou ho a přemístí... Můžemi někdo prosím vysvětlit, proč?! Proč by někdo dělal něco takovýho?! Ok, uvažujme to, že jsme to nějak střebali, teď už tu nic hrozného ne- Je. Tohle se stane, když chcete zobrazit víc výsledků na stránce, ale když chcete zobrazit další stránku, tak se stránka načte znovu... Jo to zní jednodušeji, **ale proč by to někdo dělal, když už tu je ta druhá cesta, která už je hotová, (bohužel) funguje?!**<br>
Tak toto bylo moje vyjádření k Bakalářům :)

# Endpointy
Zde jsou poznámky, co se kam a proč posílá a jak se z toho dostávají věci, co chceme...
## **/login**
#### Klíč: `login`
Přihlašovací stránka - formulář s jménem a heslem. Měl by sem redirectovat i request/response na root (tzn. "/").
Zároveň slouží i pro ověřování údajů:
```http
POST /login HTTP/1.1
username=*JMENO*&password=*HESLO*
```
Při přihlašování ručně se posílají navíc ještě parametry `"&returnUrl=&login="`, ale pro přihlášení není potřeba.
Při úspěčném přihlášení přesměruje na `/dashboard`.

## **/logout**
#### Klíč: `logout`
Odhlásí uživatele. Toť vše. Neposíláme žádný parametry, jen requestneme stránku.

## **/dashboard**
#### Klíč: `dashboard`
Pro normálního uživatele rychlý přehled. Pro nás nic zajímavého.
Dá se použít jakožto "jistá" stránka. `BakariAPI` ji používá jako stránku pro zjištění informací o uživateli. (teda zatím ne, ale plánuje se)

## **/next/komens.aspx**
#### Klíč: `komens`
Stránka pro Komens (pošta/zprávy). Odsud dokážeme vytěžit IDčka *všech* zpráv. Můžeme si vzít i něco víc, ale `BakalariAPI` toho nevyužívá, protože pomocí IDčka zprávy můžeme dostat všechny informace o zprávě (tzn. i něco, co tu není). Celý request co `BakalariAPI` může vytvořit je:
```http
GET /next/komens.aspx?s=custom&from=*DATUM_OD*&to=*DATUM_DO* HTTP/1.1
```
Popřípadě:
```http
GET /next/komens.aspx?s=custom&from=*DATUM_OD*&to=*DATUM_DO*&l=o HTTP/1.1
```
První request je na získání příchozích zpráv, druhý pro odchozí. Změna je pouze v přidání paramteru `"l"` s hodnoutou `"o"` (zkráceně `"odeslane"`, ale funguje i jen `"o"`). Nutno dodat, že zatím nebylo zjištěno, zda přijaté a odeslané zprávy mají stejnou strukturu (resp. zda se na ně dá uplatnit stejný postup parisingu).<br>
Datum je ve formátu `"DDMMYYYY"`. Nejmenší hodnota, co se za něj může dosadit je 1. 1. 1753, tedy `"01011753"`. Pravděpodobně  běží na starém SQL serveru (nebo používají starý věci, který používat nemají), který nepodporuje dřívější datum kvůli "chybějícím" dnům. Ref: [https://stackoverflow.com](https://stackoverflow.com/questions/3310569/what-is-the-significance-of-1-1-1753-in-sql-server)<br>
Teď jak získat data co potřebujem (resp. pouze ID zpráv). To co nás zajímá, tak je `<div>` s atributem `id=message_list_content`, kde je list, jehož položky obsahují v atributu `data-idmsg` ID zprávy. Ta zajímavá HTML část odpovědi je tedy něco jako:
```html
<div ... id="message_list_content" ...>
    <ul>
        <li>
            <table ... data-idmsg="ID_ZPRAVY" ...> ... </table>
        </li>
        <li>
            <table ... data-idmsg="ID_ZPRAVY" ...> ... </table>
        </li>
        <li>
            <table ... data-idmsg="ID_ZPRAVY" ...> ... </table>
        </li>
        ...
    </ul>
</div>
```
Všechny ID zpráv začínají písmenem "U", resp. nenašel jsem příkad, kde by tomu tak nebylo. Je dost možný, že podle jejich ID jde něco poznat (občas nalezen pattern IDček, ale nebyl ještě zkoumán).

## **/next/komens.aspx/GetMessageData**
#### Klíč: `komens_get`
Tento endpoint je pro nás čistý zdroj dat. Manuálně se k němu nedostanete a musíte "odchytit" provoz při zobrazování zprávy. Posíláme na něj POST request s IDčkem zprávy a kontextem (poznámka k němu dál) zakodované v JSONu a vrátí se nám JSON data o dané zprávě. Request vypadá následovně:
```http
POST /next/komens.aspx/GetMessageData HTTP/1.1
{'idmsg':'*ID_ZPRAVY*', 'context':'prijate'}
```
Hodnotu klíče `context` zatím nebylo zkoušeno měnit či odstranit. V návaznosti na odstavec ohledně odeslaných zpráv u endpointu `/nex/komens.aspx` - na první pohled je zřejmé, že klíč `context` má tendenci se změnit, když se bude jednat o odeslanou zprávu (a ne přijatou). Ale jelikož odeslané zprávy zatím nebyly otestovány, tak nelze zdokumentovat.<br>
Zpátky dostaneme něco jako (pro čitelnost zformátováno):
```JSON
{
   "CaptionText":"Obecná zpráva",
   "Cas":"1.12.2020 15:00",
   "Files":[
      
   ],
   "Id":"*ID_ZPRAVY*",
   "Jmeno":"*ODESILATEL*",
   "Kind":"OBECNA",
   "MessageText":"*TEXT_ZPRÁVY*",
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
   "RecipientsDontReadName":null,
   "RecipientsReadCount":null,
   "RecipientsReadName":null,
   "ShowReadCount":false,
   "ShowConfirmButton":true
}
```
Pokud má zpráva přílohu/přílohy, tak klíč `"Files"` má array objektů souborů. Objekt souboru vypadá následovně:
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
Vypadá to, že soubor se váže k určité zprávě (klíč `"idmsg"` se shoduje s ID zprávy). Pro klíč `"path"` se zatím nenašlo využití.

## **/next/komens.aspx/SetMessageConfirmed**
#### Klíč: `komens_confirm`
K tomuto endpointu se opět dostanete po odchycení requestů při potvrzování zprávy. Opět se jedná o POST request a opět s IDčkem zprávy zakódované v JSONu:
```http
POST /next/komens.aspx/SetMessageConfirmed HTTP/1.1
{'idmsg':'*ID_ZPRAVY*'}
```
Zpět dostáváme zprávu v JSONu (nejspíše) o úspěchu potvrzení (zatím netestováno chybné potvrzení (tzn. špatné ID zprávy)):
```JSON
{"d": true}
```
Co znamená `"d"`se nezjistilo.

## **/next/getFile.aspx**
#### Klíč: `file`
Endpoint pro stahování souborů (z Komensu). Posílá se get request s parametrem `"f"` s hodnotou IDčka souboru. Request vypadá následovně:
```http
GET /next/getFile.aspx?f=*ID_SOUBORU* HTTP/1.1
```

## **/next/prubzna.aspx**
#### Klíč: `grades`
*(Ano, je to **prubzna**, není to překlep (jakože nejspíš je, ale ne můj)...)*<br>
Pro normálního uživatele soupis známek. Pro nás je to zdroj známek:
```http
GET /next/prubzna.aspx?subt=obdobi&dfrom=*DATUM_OD* HTTP/1.1
```
Stejně jako u Komens, tak i zde můžeme zadat datum (jinak se počítá pouze současné pololetí) - zde pro to musíme přidat `"?subt=obdobi"` abychom aktivovali filtr a pak datum ve formátu `"YYMMDD0000"` (4 nuly na konci pravděpodobně hodiny a minuty, ale s známky nemají čas, pouze datum, takže k ničemu) do parametru `"dfrom"`.<br>
A kde máme naše data? Někde v HTML je `<div>` s `id="cphmain_DivBySubject"` (tento `<div>` má jako parrenta `<div>` s `id="predmety"`, který je v `<main>`) v němž bordel. Nejlepší bude asi diagram:
```html
<div id="cphmain_DivBySubject"> -> <div class="predmet-radek"> -> <div class="znamky">
                                -> <div class="predmet-radek"> -> <div class="znamky">
                                -> <div class="predmet-radek"> -> <div class="znamky">
```
*Pozn.: Nejsou to jediné atributy, které mají*<br>
*Pozn.: Divy, které mají `class="predmet-radek"` mají i ID, což je pravděpodobně ID předmětu (ale zatím nenalezena souvilost)*<br>
A `<div class="znamky">` obsahuje další `<div>`, které mají jako `id` ID známky a v jejichž atributu `data-clasif` se nachází JSON data zakódovaná v HTML (naštěstí `bs4` automaticky HTML entity dekóduje). JSON pak vypadá takto:
```JSON
{
   "ShowCaption":true,
   "ShowTheme":false,
   "ShowType":false,
   "ShowWeight":false,
   "bodymax":0,
   "caption":"Test z malé násobilky",
   "id":"*25L4KBF0{",
   "IsNew":false,
   "maxvaha":1,
   "minvaha":1,
   "nazev":"Matematika",
   "oznaceni":"Test",
   "poznamkakzobrazeni":"",
   "ShowOrder":true,
   "strdatum":"1.1.2020",
   "datum":"0001-01-01T00:00:00+01:00",
   "strporadivetrideuplne":"1. - 13. (∑ 13, ø 1)",
   "typ":"T",
   "udel_datum":"1.1.2020",
   "vaha":1,
   "calculatedMark":"",
   "MarkText":"2",
   "PointsText":"",
   "MarkTooltip":null,
   "VelikostZnamkyCssClass":"velky"
}
```
Tenhle JSON je bordel sám o sobě... "Hlavní název" známky je klíč `"caption"`. Další info ke známce je v klíči `"poznamkakzobrazeni"` a také v klíči `"MarkTooltip"`. Klíč `"datum"` je úplně k ničemu a je pořád stejný. Za to klíče `"strdatum"` a `"udel_datum"` oba obsahují (nějaký) datum, který je ve většině případě stejný (ale ne konstantní), ale může se i lišit (normálnímu uživateli se může ale zobrazit pouze klíč `"strdatum"`). Předmět má pak klíč `"nazev"` a hodnota známky má pak klíč `"MarkText"`. Další klíče jsou snad pochopitelné (i když třeba osobně nechápu klíč `"bodymax"`).

## **/sessioninfo**
#### Klíč: `session_info`
Endpoint který je pro normálního uživatele opět nedostupný. Normálně se sem posílá v určitém intervalu (jaký je se nezjistilo a je možný, že je dynamický) GET request s parametrem `"_"`, který má hodnoutu UNIX timestampy klienta. Z testování se má za to, že tato UNIX timestamp je k ničemu a endpoint funguje i bez toho. Vrací se JSON v podobě:
```JSON
{"success":true,"error":"","data":{"remainingTime":500.12345,"sessionDuration":15.0}}
```
Pro nás má užitek jen informace o tom, kolik zbývá (`"remainingTime"`) a jak dlouhá je maxiálně sesssion bez prodloužení (`"sessionDuration"`).<br>
Klient ověřuje, jestli `"remainingTime"` je pod určitou hranicí a popř. zobrazí dialog ve smyslu *"Jste tu? Jestli jo, zmáčkmi tlačítko"*, popř. (pokud `"remainingTime"` je 0) zobrazí dialog *"Jste dlouho offline a proto jsme vás z DŮVODU BEZPEČNOSTI odhlásili. (+ tlačíko)"*.

## **/sessionextend**
#### Klíč: `session_extend`
Normálně nedostupný, posílá se na něj GET request s parametrem `"_"`, který má hodnotu UNIX timestampy uživatele a který je opět k ničemu a opět endpoint funguje i bez toho. Pokud na něj pošleme takovýto request, tak prodlouží délku současné session, ale je v případě, kdy už je session za (možná i "v") půlkou své životnosti.<br>
*Pozn.: Je možný, že je potřeba, aby životnost session byla za/v 450s (= 7,5 minut). Přestože je tato možnost nepravděpodovná, je možná - Bylo testováno jen na serveru, kde délká session je 900s (= 15 minut).*

## **/Collaboration/OnlineMeeting/MeetingsOverview**
#### Klíč: `meetings_overview`
Normálně zobrazuje přehled nadcházejících online schůzek. Pro nás zdroj IDček schůzek a to hned dvěma způsoby, které dávají rozdílné věci. Já začnu tím "druhým" (druhý znamená, že jsem na něj přišel jako později) protože u prvního máme něco navíc...<br>
Způsob č. 2 je využítí "API", které na to mají. Uděláme POST request na tento endpoint, který vypadá nějak takto:
```http
POST /Collaboration/OnlineMeeting/MeetingsOverview HTTP/1.1
TimeWindow=FromTo&FilterByAuthor=AllInvitations&MeetingFrom=*DATUM_OD*&MeetingTo=*DATUM_DO*
```
Tento request by zjištěn opět přes odchyt výsledků filtrování a následně vyzkoušeno, které parametry je potřeba a které lze vyhodit. Parametry `TimeWindow` a `FilterByAuthor` přeskočím, protože nebyla nalezena cesta jak je užít nějak jinak - prostě je potřebujeme, abychom "aktivovali" tohle "API" a nevrátilo se nám HTML namísto JSONu. `MeetingFrom` a `MeetingTo` jsou data na filtraci. Originální formát je `%Y-%m-%dT%H:%M:%S%z`, ale údaj se časového pásma se dá postrádat. Minimum je `0001-01-01T00:00:00` (když za rok dosadí "0000", tak se (podle dat z responsu) převede na "0001") a maximum `9999-12-31T23:59:59`. Odpověď je v JSONu a vypadá takto:
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
            "HasExternalChange":false
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
Ano, response je velký... A ano - přes 90% hodnot je neplatných (např. asi tak všechno info o schůzce). Jediné údaje, kterým se dá věřit, tak jsou schůzek `"Id"`, `"MeetingStart"`, `"Title"`, `"OwnerId"` a `"OwnerName"`. Naštěstí chceme tenhle response jen kvůli IDčkům o schůzkám, které můžeme využít u endpointu `/Collaboration/OnlineMeeting/Detail/`.<br>
Tak to by byl jeden způsob jak získat IDčka schůzek. Druhý způsob je scraping. Sice je to náročnější scrapping, ale taky z toho můžeme získat o dost více informací. Zde totiž musíme scrapnout `<script>` tag. `BakalariAPI` hledá daný `<script>` tag bruteforcem - projde všechny `<script>` tagy v `<head>` tagu a pokud najde v JS tohoto tagu string `"var model = "`, tak považuje tento tag za správný. Dál projíždí celý JS tohoto tagu a hledá řádku, která (, když se osekají mezera a taby,) začíná `"var meetingsData = "`. Pokud takovou řádku najde, tak tento začátek odsekne a zbyde jen JSON schůzek (a středník na konci). JSON vypadá takto:
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
        "HasExternalChange":false
    },
]
```
Údaje o schůzkách jsou stejně kvalitní jako u předchozího způsoby (90% jsou invalidní data). Ale máme IDčka schůzek (ale jen nadcházejících). No ale v tomto `<script>` tagu se nachází ještě seznam všech studentů na škole. Ano, je to tak - a absolutně nemám ponětí, co tam dělá, jelikož jsem nenarazil na jedinou věc, kde se používá... Každopádně nyní hledáme řádku začínající (opět po osekání mezer a tabů) `"model.Students = ko.mapping.fromJS("`. Kdyý ji najdeme a osekneme začátek a konec (tedy `");"`), tak získáme JSON studentů:
```JSON
[
    {
      "Id":"*ID_STUDENTA*",
      "Name":"*JMÉNO*",
      "Surname":"*PŘÍMENÍ*",
      "Class":"*TŘÍDA*",
      "FullName":"TŘÍDA JMÉNO PŘIJMENÍ"
   },
   ...
]
```
Klíč `"Name"` popřípadě obsahuje i druhé jméno. Klíč `"FullName"` je poskládán z ostatních hodnot.<br>
*Pozn.: Pool ID pro studenty, učitele a možná něco dalšího je nejspíše stejný.*

## **/Collaboration/OnlineMeeting/Detail/**
#### Klíč: `meetings_info`
Jeden z další enpointů, který normální uživalel nevidí. Slouží k získání informací o schůzce s určitím ID. Dotaz je GET request:
```http
GET /Collaboration/OnlineMeeting/Detail/*ID_SCHUZKY* HTTP/1.1
```
Vrací se nám JSON:
```JSON
{
   "success":true,
   "error":"",
   "data":{
      "Id":*ID_SCHUZKY*,
      "MeetingId":"AQMkADYyZtQxNTFmLWU0NMEtmDYyZi05MmYWLTgyZjQ4NTQyOTg5YQBGAAADw-umPgBqOEi5DCaofeuo1gcAMC8d3HCMpEijse0_agIBP7AAAgENAAAAMC8d3HCMpEijse2_agIBPgAB_e8TBQAAAA==",
      "MeetingStart":"*START_SCHŮZKY*",
      "MeetingEnd":"*KONEC_SCHŮZKY*",
      "Title":"*NÁZEV_SCHŮZKY*",
      "Details":"*OBSAH_ZPRÁVY_SCHŮZKY*",
      "OwnerId":"*ID_POŘEDATELE*",
      "Error":null,
      "RecipientTypeCode":"ZU",
      "RecipientCode":"1022FC",
      "Participants":[
         {
            "PersonId":"*ID_OSOBY*",
            "PersonName":"*JMÉNO_OSOBY*",
            "Readed":"*ČAS_PŘEČTENÍ*",
            "RecipientRole":2,
            "Emails":null
         },
         {
            "PersonId":"*ID_OSOBY*",
            "PersonName":"*JMÉNO_OSOBY*",
            "Readed":null,
            "RecipientRole":2,
            "Emails":null
         },
         {
            "PersonId":"*ID_OSOBY*",
            "PersonName":"*JMÉNO_OSOBY*",
            "Readed":"*ČAS_PŘEČTENÍ*",
            "RecipientRole":1,
            "Emails":null
         },
         ...
      ],
      "ParticipantsReadedCount":10,
      "ParticipantsTotalCount":29,
      "OwnerName":null,
      "ParticipantsListOfRead":[
         {
            "PersonId":"*ID_OSOBY*",
            "PersonName":"*JMÉNO_OSOBY*",
            "Readed":"*ČAS_PŘEČTENÍ*",
            "RecipientRole":2,
            "Emails":null
         },
         ...
      ],
      "ParticipantsListOfDontRead":[
         {
            "PersonId":"*ID_OSOBY*",
            "PersonName":"*JMÉNO_OSOBY*",
            "Readed":null,
            "RecipientRole":2,
            "Emails":null
         },
         ...
      ],
      "MeetingStartDate":"*START_SCHŮZKY*",
      "MeetingStartTime":"*START_SCHŮZKY*",
      "MeetingEndDate":"*KONEC_SCHŮZKY*",
      "MeetingEndTime":"*KONEC_SCHŮZKY*",
      "IsOver":false,
      "IsOwner":false,
      "RecipientsDisplayName":"žáci",
      "CanEdit":false,
      "IsInvitationByEmailOrKomens":true,
      "JoinMeetingUrl":"*URL_NA_PŘIPOJENÍ*",
      "HasExternalChange":false
   }
}
```
Výsledek je zase obalen jakýmsi "statusem" a data, která nás zajímají jsou pod klíčem `"data"`. Klíč `"Id"` je ID schůzky. Účel klíče `"MeetingID"`, ale vypadá, jako nějaký Base64. Klíče `"MeetingStart"`, `"MeetingStartDate"` a `"MeetingStartTime"` obsahují stejnou hodnotu ve formátu `%Y-%m-%dT%H:%M:%S%z"`. Stejně tak jsou si rovny klíče `"MeetingEnd"`, `"MeetingEndDate"` a `"MeetingEndTime"` (i stejný formát času). Název schůzky je v klíči `"Title"`, zpráva ke schůzce je v klíči `"Details"` a ID pořadatele je v klíči `"OwnerId"`. Seznam (pozvaných) účastníků je v klíči `"Participants"` (nachází se v něm i pořadatel). Jednotlivé položky v tomto seznamu mají ID v klíči `"PersonId"`, jméno je v klíči `"PersonName"`. Pokud si učástník pozvánku přečetl, tak pod klíčem `"Readed"` je čas přečtení ve formátu `%Y-%m-%dT%H:%M:%S.%f`.<br>
*Pozn.: Přestože je zde napsáno, že poslední čast hodnoty je `%f`, tak tomu tak v Pythonu není. Délka zlomku sekundy se liší a může přesahovat maximální délku pro `%f` v Pythonu. `BakalariAPI` řeší tento problém tím, že zlomky sekundy odsekává.*<br>
Klíč `"RecipientRole"` určuje "postavení"/"role" - Hodnota "1" je pořadatel, hodnota "2" účastník. Užitek klíče `"Emails"` není znám. Mimo seznamu v klíči `"Participants"` jsou tu ještě 2 další seznamy: `"ParticipantsListOfRead"` obsahující účastníky, kteří už pozvánku četli/viděli (bez pořadatele) (tedy ty, u kterých klíč `"Readed"` není `null`) a `"ParticipantsListOfDontRead"` obsahující zbytek (opět bez pořadatele). V klíči `"ParticipantsTotalCount"` je počet účastníku bez pořadatele. Poslední zajímavý klíč je `"JoinMeetingUrl"`, ve kterém se nachází URL na připojení na schůzku.<br>
*Pozn.: Klíč `"OwnerName"` je vždy `null` a pokud chceme jméno pořadatele, musíme prohledat seznam v klíči `"Participants"` a najít položku, kde se klíč `"Id"` shoduje s `"OwnerId"` nebo kde klíč `"RecipientRole"` je roven "1".*<br>
Pokud ID schůzky neexistuje, je response HTTP 302 (Found) a přesměrování na `/dashboard` endpointt s GET parametrem `"e="` (ano, parametr je prázdný).<br>
Pokud ID schůzky existuje, ale schůzka neexistuje (nebo tak něco), je response HTTP 500 (Internal Server Error) a JSON je následující:
```JSON
{
   "success":false,
   "error":"Nepodařilo se načíst detail schůzky.",
   "data":null
}
```

## **/next/ukoly.aspx**
#### Klíč: `homeworks`
Zobrazuje seznam úkolů (defaultně pouze "aktivní" a neoznačené jako hotové). Pro nás to je seznam těchto IDček. (A také je to pro nás jeden z nejhorších endpoitů, jelikož je to vlastně ASPX forma.) Jak získáme tyhle IDčka? Někde v HTML responsu je tabulka s atributem `id="grdukoly_DXMainTable"`. Ta má v sobě řádky s úkoly, ale má v sobě i řádek s "hlavičkou" tablky (normálně bych se divil, proč tu není `<thead>` a `<tbody>` (jako u jiných tabulek), ale jelikož to jsou Bakaláři, tak to jsem schopnej relativně "snadno" (resp. normálně) pochopit). Po zbavení se prvního řádku nám zbydou jen řádky, které chceme. Řádek vypadá takto:
```html
<tr id="grdukoly_DXDataRow0" title="zbývá méně než 7 dní." class="dxgvDataRow_NextBlueTheme celldo7 _electronic">
   <td id="grdukoly_tccell0_0" class="dxgv">
      <div style="display: inline-flex;">
         <div class="homework-ico noicon"></div>
         <div>*Datum odvzdání*</div>
      </div>
   </td>
   <td class="dxgv">*Předmět*</td>
   <td class="_checkUrl dxgv">*Zadání/Text/Informace úkolu*</td>
   <td id="grdukoly_tccell0_3" class="dxgv">*Datum zadání*</td>
   <td id="grdukoly_tccell0_4" class="overflowvisible dxgv">
      <link href="css/komens_message_detail.css?v=20201023" rel="stylesheet" />
      <div>
         <span class="message_detail_header_paper_clips_menu attachment_dropdown _dropdown-onhover-target" style='{{if PocetFiles==0 }}visibility: hidden; {{/if}}'>
            <span class="message_detail_header_paper_clips ico32-data-sponka"></span>
            <span class="message_detail_header_paper_clips_files dropdown-content left-auto">
               <!-- Seznam příloh ... (Tento komentář se v responsu nevyskytuje :) ) -->
               <a href='getFile.aspx?f=*ID_SOUBORU*' target="_blank">
                  <span class="attachment_name">*NÁZEV_SOUBORU*</span>
                  <span class="attachment_size">Velikost souboru (v readable formátu)</span>
               </a>
               <!-- Konec seznamu příloh (Tento komentář se v responsu nevyskytuje :) ) -->
            </span>
         </span>
      </div>
   </td>
   <td id="grdukoly_tccell0_5" class="dxgv">
      <div class="checkbox text-center">
         <input id="chkbox_*ID_ÚKOLU*" type="checkbox" value="False" onclick="markAsDone('*ID_ÚKOLU*', '*ID_STUDENTA*', $(this));" />
         <label for="chkbox*ID_ÚKOLU*"></label>
      </div>
   </td>
   <td id="grdukoly_tccell0_6" class="tac dxgv" style="border-right-width:0px;">
      <span class="link fa fa-envelope-open-o padding-5" target='*ID_ÚKOLU*' onclick="showOdevzdani('*ID_ÚKOLU*', $(this));"></span>
   </td>
</tr>
```
Nás zajímá poslední sloupek (pro uživatele je to "vlaštovka" na odeslání úkolu). Ten totiž obsahuje atribut `target`, který má ID úkolu.

## **/HomeWorks/MarkAsFinished**
#### Klíč: `homeworks_done`
Endpoint, který se stará o to, aby se úkol o(d)značil jako hotový. Normálně nedostupný. Posílá se POST request:
```http
POST /HomeWorks/MarkAsFinished HTTP/1.1
homeworkId=*ID_UKOLU*&completed=*STAV*&studentId=*ID_STUDENTA*
```
Zvláštní je, že endpoint přijmá/vyžaduje ID studenta, avšak to vypadá, že se na něj nehledí. Parametr `"completed"` určuje, jaký stav se má "nastavit" (`true` je hotovo, `false` je nehotovo). Response vypadá takto:
```json
{"success":true,"error":"","data":null}
```
Další zvláštností je, že takto vypadá response i když je ID úkolu nebo ID studenta neplatný.