# **/next/prubzna.aspx**
### Klíč: `grades`
*(Ano, je to **prubzna**, není to překlep (tedy nejspíš je, ale ne můj)...)*

# Metadata
| Název                             | Hodnota                    |
|-----------------------------------|:--------------------------:|
| Verze Bakalářů                    | 1.36.1214.1                |
| Datum verze Bakalářů              | 14. 12. 2020               |
| Datum poslední změny dokumentu    | 20. 12. 2020               |
| Potřeba Selenia?                  | Ne                         |

# Přehled
Pro normálního uživatele přehled známek. Známky jsou v "tabulce". A pro nás je to možnost odkud lze získat známky. Lze aplikovat filtr přes parametr `subt` a `dfrom` - defaultně se zobrazují známky je z tohoto pololetí.

# Request
```http
GET /next/prubzna.aspx?subt=obdobi&dfrom=*DATUM_OD* HTTP/1.1
```
Lze poslat i obyčejný request bez parametrů (vrátí se známky z tohoto pololetí), avšak máme možnost určit/omezit dobu, ze které chceme získat známky. `*DATUM_OD*` je ve formátu `%y%m%d0000`, např. `2031120000` (= 31. 12. 2020) (4 nuly na konci pravděpodobně hodiny a minuty, ale známky nemají čas, nýbrž pouze datum, takže asi k ničemu) a funguje pouze, pokud je přítomen i parametr `subt` s hodnotou `obdobi`.

# Response
Vždy se vrací HTML.

## Extrakce dat - HTML => JSON
Za tu dobu, co toto vyvíjím, tak se struktura několikrát změnila, a proto jsem postup od původního způsobu, který postupoval krok po kroku (resp. element po elementu), změnil tak, aby byl co nejjednodušší/nejuniverzálnější: Chceme najít všechny elementy (zatím to jsou pouze `<div>` tagy), které mají `data-clasif` atribut. V tomto atributu je JSON ve kterém jsou data o známce.


JSON vypadá takto:
```JSON
{
   "ShowCaption":true,
   "ShowTheme":false,
   "ShowType":false,
   "ShowWeight":false,
   "bodymax":0,
   "caption":"Test kolik z malé násobilky",
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
   "MarkText":"4+",
   "PointsText":"",
   "MarkTooltip":null,
   "VelikostZnamkyCssClass":"velky"
}
```
Popis klíčů:
- `caption` - "Název" známky
- `id` - ID známky
- `IsNew` - Indikuje, zda je známka nová či ne; `BakalářiAPI` tuto hodnotu nepoužívají (nezjistilo se (ani o to nebyl pokus), jak se určuje tato hodnota)
- `nazev` - Předmět
- `oznaceni` - Typ známky v "delší podobě", viz tabulka dál
- `poznamkakzobrazeni` - Popisek ke známce; Tento text dokonce uživatel není schopen vidět (nikde se nezobrazuje)
- `strdatum` - Datum (něčeho), většinou stejný jako `udel_datum`, ale mohou se lišit (někdy je větší `strdatum`, někdy `udel_datum`)
- `datum` - Tuto hodnotu ignorujte, vždycky má stejnou hodnotu `0001-01-01T00:00:00+01:00`
- `strporadivetrideuplne` - Pořadí ve třídě; Netuším, jak se to počítá ani pořádně nevím, co to znamená eShrug
- `typ` - Typ známky v "krátké podobě", viz tabulka dál
- `udel_datum` - Datum (něčeho), většinou stejný jako `strdatum`, ale mohou se lišit (někdy je větší `udel_datum`, někdy `strdatum`)
- `vaha` - Váha známky, kde `1` je (asi) nejnižší
- `MarkText` - Hodnota známky; Může obsahovat `+` nebo `-`, poznamenáno, kdyby někdo chtěl tuto hodnotu zkoušet parsovat ze stringu na číslo

### Typ, označení
Vypozorována závislost mezi hodnotami klíčů `typ` a `oznaceni`. Je možné, že mohou existovat specifické typy a označení v rámci jedné školy/jedné instance Bakalářů.
| Typ    | Označení                 |
|:------:|--------------------------|
| T      | Test                     |
| S      | Seminární práce          |
| D      | Domácí úkol              |
| J      | Jiné                     |

# Výzkum
Při hledání způsobu, jak parsovat známky byla v HTML, při manuálním prohledáváním zdroje stránky, nalezena JSON data (= data v atributu `data-clasif`). Tyto data pak byla zanalyzována a byl odvozen význam jednotlivých klíčů. Poznatky o filtrování byly získány manuální zkoušením a pozorováním requestů. Tabulka typ-označení byla nejdříve vypozorována, následně ověřena při možnosti pohledu na kontextovou nabídku z pohledu učitele.