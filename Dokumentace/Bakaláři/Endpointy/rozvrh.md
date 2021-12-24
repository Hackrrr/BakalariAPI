# **/next/rozvrh.aspx**
### Klíč: `rozvrh`

# Metadata
| Název                             | Hodnota                    |
|-----------------------------------|:--------------------------:|
| Verze Bakalářů                    | 1.45.1214.2                |
| Datum verze Bakalářů              | 14. 12. 2021               |
| Datum poslední změny dokumentu    | 24. 12. 2021               |
| Potřeba Selenia?                  | Ne                         |

# Přehled
Stránka zobrazující rozvrh spolu se změnami.

# Request
```http
GET /next/rozvrh.aspx?s=*DRUH* HTTP/1.1
```
Parametr `"s"` určuje, jaký rozvrh se zobrazí. Možné hodnoty jsou `"next"` (následující týden), `"perm"` (stálý) a `"cal"` (současný týden, ale s výběrem dnů), jiné hodnoty (nebo nepřítomnost parametru) vyustí v zovrazení rozvrhu na současný týden.


# Response
Vrací se HTML.

## Extrakce dat - HTML => JSON
Ze získaného HTML chceme vzít elementy (`<div>`) s třídou `.day-item-hover`. Tyto elemetny obsahují v atributu `"data-detail"` JSON hodiny. JSON se liší v závislosti na klíči `type`, kde jsou možné tři hodnoty - `"atom"` ("normální" hodnota), `"removed"` (hodina byla odstraněna) a `"absent"` (asi nahrazení/přidání hodiny?). JSON pro `"atom"`:
```json
{
   "type":"atom",
   "subjecttext":"Matematika | po 20.12. | 1 (8:00 - 8:45)",
   "teacher":"Ing. Jan Novák",
   "room":"05",
   "group":"",
   "theme":"Téma",
   "notice":"",
   "changeinfo":"",
   "homeworks":[
      "Úkol 1",
      "Úkol 2"
   ],
   "absencetext":"",
   "identcode":"1202112200322FC10UTBP9"
}
```
Klíče:
- `subjecttext` - String obsahující informace o předmětu a datu+času hodiny. Je svislou čarou rozdělen na tři části:
  - Název hodiny - Může být lokalizován (pokud je to nastaveno (defaultně vypnuto))
  - Den+Datum - Tato čás je plně lokalizována - jak názvy dnů, tak formát data; Pokud zobrazujeme stálý rozvrh (`"?s=perm"`), není uveden datum
  - Pořadí hodiny - První číslo je pořadí/číslo hodiny, v závorce je uveden začátek a konec hodiny
- `teacher` - Učitel
- `room` - Název/Označení třídy/učebny
- `group` - Označení skupiny pro kterou je daná hodina nebo prázdný string
- `theme` - Téma; Osobně bych to označil za název hodiny
- `notice` - Další případná poznámka
- `changeinfo` - Lokalizovaná informace o změně, např. "Suplování (MAT, NO)" ("NO" znamená "Novák (Jan)")
- `homeworks` - Array úkolů pro daný předmět - vypadá to, že ačkoli je úkol dán na určitou hodinu/datum, stejně se zobrazí u všech na hodin daného předmětu a vypadá to, že zobrazení s kalendářem (`"?s=cal"`) neobsahuje úkoly nikdy (resp. obsahuje vždy prázdnou array); Každý prvek v seznamu je string s textem úkolu, který odpovídá text z [`homeworks` endpointu](homeworks.md)
- `absencetext` - Lokalizový string se stavem absence, pravděpodobně jsou možné jen určité hodnoty - prázdný string (žádná obsence), `"omluvená absence"`, ... (další nemám k dispozici)
- `identcode` - ID hodiny (viz dále)

U stálého rozvrhu obsahují klíče `theme`, `notice`, `theme`, `changeinfo` a `absencetext` vždy prázdný string a klíč `homeworks` vždy prázdnou array. Pokud na serveru Bakalářů nejsou nastaveny/zapnuty úkoly, klíč `homeworks` je vždy `null`.

JSON pro `type` `"removed"` a `"absent"`:
```json
{
   "type":"absent",
   "subjecttext":"st 22.12. | 8 (14:10 - 14:55)",
   "absentinfo":"jiný",
   "removedinfo":""
}
```
Klíč `"subjecttext"` je skoro stejný jako u `type` `"atom"`, liší se v tom, že chybí první část (název předmětu). Klíče `"absentinfo"` a `"removedinfo"` obsahují info o příčině změny - když se jedná o `type` `"absent"`, je pro informaci použit klíč `"absentinfo"`, když je `type` `"removed"`, použije se `"removedinfo"`.

## Extrakce dat - HTML => Volné dny
Speciální případ jsou volné dny. U nich totiž neexistuje JSON. "Záznam" pro volné dny v rozvrhu vypadá takto:
```html
<div class="day-row normal" style="height:87px;">
	<div class="odd-day-row"> <!-- Tenhle <div> je zde pro každou lichou řádku (tedy ÚT a ČT), protože asi někdo CSS modifikátory -->
		<div class="clearfix">
			<div class="day-name odd-name normal" style="height:87px;">
				<div> čt
					<br>
               <span>23.12.</span>
            </div>
			</div>
         <!-- Místo následujícího <div>u jsou normálně <span> tagy s jednotlivými hodinami -->
			<div class="day-item-volno border-levy border-horni border-pravy">
				<div class="empty dayoff">Prázdniny </div>
			</div>
		</div>
	</div>
</div>
```
Strategie je tedy najít třídu `.day-item-volno` (`<div>` tag). Child `<div>` obsahuje zprávu/důvod, "sourozenec" obsahuje datum/den, pro který tohle platí.

## `identcode` alias ID hodiny
Ok, tady si musi pogratulovat, protože tohle byla doslova detektivní práce a jsem na to poměrhně hrdý. Nyní ale k věci...

ID hodiny ukrývá dost informací. Konkrétně obsahuje: datum hodiny, číslo/pořadí hodiny, skupinu, předmět, učitele a další dva (nebo tři) údaje, které nevím co jsou (protože se nemění, tak nemám možnost zjistit co jsou zač). ID má 22 znaků (A až Z, 0 až 9 a mezera) a lze ho rozdělit části:
- 1\. znak je číslo; Až na třídní hodninu (zde je trojka) je zde vždy jednička a nevím k čemu je
- Dalších 8 znaků (2.-9.) je datum hodiny ve formátu `YYYYMMDD`; Pokud se jedná o hodinu ve stálém rozvrhu, jsou zde mezery
- 2 následující čísla je pořadí hodiny; Zdá se, že k tomuto číslu je přičítána dvojka, protože první hodina má hodnotu "03"
- Následují 2 další znaky (asi čísla), které ve všech případech byly stejné a které nevím k čemu slouží (napadá mě ozančení třídy, což by i dávalo smysl I guess (jak samostatně, tak i v souvislosti s další hodnotou))
- Další 2 znaky označují ID(?) skupiny (pro kterou je daná hodina)
- Další 2 znaky označují ID předmětu (může obsahovat i mezeru; tipl bych si, že mezera bude u "základních" předmětů např. čeština, angličtina (přestože u matematiky tomu tak není))
- Posledních 5 znaků je ID učitele

Pozn.: Tohle je jeden z nějvětších poznatků, jelikož se ověřila existence dalších ID (předměty, učitelé, ...). Většinou jsem předpokládal, že ID existuje, ale nikde se nenalezl údaj o kterém říct "ano, tohle je 100% ID tohoto objektu". U předmětů jsem ID již předtím našel u známek, ale mohl jsem pouze tipnout, že je to ID předmětu. ID učitelů se samozřejmě předpokládalo, ale ID u schůzek mohlo být nějaké divné ID na spojení platformy schůzek a Bakalářů. Také se ukázalo, že "uživatelský hash" je pravděpodobně složen z několika částí (tenhle rozbor mě ještě čeká).


# Výzkum
Enpoint nalezen přes normální proklik v menu. JSON nalezen analýzon HTML. Možné hodnoty `type` odvozeny od šablon, které jsou obsašeny v HTML. Info o ID hodiny bylo zjištěno pozorováním souvislostí. 
