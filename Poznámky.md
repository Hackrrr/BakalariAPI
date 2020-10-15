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
Přihlašovací stránka - formulář s jménem a heslem. Měl by sem redirectovat i request/response na index (tzn. "/").
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
### **Vyžaduje se přeskoumání - Pravděpodobně funguje jen od určité (prcentuální/zbývající) doby**
V podstatě stejný jak **`/sessioninfo`**. Normálně nedostupný, posílá se na něj GET request s parametrem `"_"`, který má hodnotu UNIX timestampy uživatele a který je opět k ničemu a opět endpoint funguje i bez toho. Mění se akorát "funkčnost", která ale není vidět - prodluží session (zpátky) na maximální životnost. Nevrací se nic.
## **/Collaboration/OnlineMeeting/MeetingsOverview**
#### Klíč: `meetings`
```diff
- DODĚLAT :)
```
## **/Collaboration/OnlineMeeting/Detail**
#### Klíč: `meetings_info`
```diff
- DODĚLAT :)
```