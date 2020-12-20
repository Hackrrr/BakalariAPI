# **/next/ukoly.aspx**
### Klíč: `homeworks`

# Metadata
| Název                             | Hodnota                    |
|-----------------------------------|:--------------------------:|
| Verze Bakalářů                    | 1.36.1214.1                |
| Datum verze Bakalářů              | 14. 12. 2020               |
| Datum poslední změny dokumentu    | 20. 12. 2020               |
| Potřeba Selenia?                  | Ano                        |

# Přehled
Pro normální uživatele přehled úkolů. Pro nás zdroj domácích úkolů. Jelikož tento "endpoint" je jeden velký ASP.NET formulář, tak velice doporučuji použít Selenium. Defaultně se zobrazí seznam nehotových aktivních úkolů ("aktivních" podle Bakalářů).

# Request
Posílá se GET request:
```http
GET /next/ukoly.aspx HTTP/1.1
```

# Response
Vrací se HTML, které musíme scrapovat.

# Extrakce dat - HTML => Data
Nejdříve si najdeme tabulku s ID `grdukoly_DXMainTable`.Ta má v sobě řádky s úkoly, ale má v sobě i řádek s "hlavičkou" tablky (normálně bych se divil, proč tu není `<thead>` a `<tbody>` (jako u jiných tabulek), ale jelikož to jsou Bakaláři, tak to jsem schopnej relativně "snadno" (resp. normálně) pochopit). Vezmeme si tedy `<tbody>` tag a z něho každý `<tr>` tag kromě prvního (= header). `<tr>` tag pak vypadá nějak takto:
```html
<tr id="grdukoly_DXDataRow0" title="" class="dxgvDataRow_NextBlueTheme celldo2 _electronic dxgvLVR" style="" aria-describedby="ui-id-3">
	<td id="grdukoly_tccell0_0" class="dxgv">
		<div style="display: inline-flex;">
			<div class="homework-ico noicon"></div>
			<div>*DATUM_ODEVZDÁNÍ*</div>
		</div>
	</td>
	<td class="dxgv">*PŘEDMĚT*</td>
	<td class="_checkUrl dxgv">*ZADÁNÍ_ÚKOLU*</td>
	<td id="grdukoly_tccell0_3" class="dxgv"> *DATUM_ZADÁNÍ* </td>
	<td id="grdukoly_tccell0_4" class="overflowvisible dxgv">
		<div>
         <span class="message_detail_header_paper_clips_menu attachment_dropdown _dropdown-onhover-target" style="{{if PocetFiles==0 }}visibility: hidden; {{/if}}">
            <span class="message_detail_header_paper_clips ico32-data-sponka"></span>
            <span class="mesage_detail_header_paper_clips_files dropdown-content left-auto">
               <!-- Seznam příloh ... (Tento komentář se v responsu nevyskytuje :) ) -->
               <a href="getFile.aspx?f=*ID_SOUBORU*" target="_blank">
                  <span class="attachment_name">*NÁZEV_SOUBORU*</span>
                  <span class="attachment_size">*VELIKOST_SOUBORU*</span>
               </a>
               <!-- ... -->
               <!-- ... -->
               <!-- Konec seznamu příloh (Tento komentář se v responsu nevyskytuje :) (ani ty předchozí tečky)) -->
            </span>
			</span>
		</div>
	</td>
	<td id="grdukoly_tccell0_5" class="dxgv">
		<div class="checkbox text-center">
			<input id="chkbox_*ID_ÚKOLU*" type="checkbox" value="False" onclick="markAsDone('*ID_ÚKOLU*', '*ID_STUDENTA*', $(this));">
			<label for="chkbox_*ID_ÚKOLU*"></label>
		</div>
	</td>
	<td id="grdukoly_tccell0_6" class="tac dxgv" style="border-right-width:0px;">
      <span class="link fa fa-envelope-open-o padding-5" target="*ID_ÚKOLU*" onclick="showOdevzdani('*ID_ÚKOLU*', $(this));"></span>
   </td>
</tr>
```
Myslím, že nemá cenu vysvětlovat, jak se k daným datům dostat... Zmíním jen zákeřnost u hodnoty `*DATUM_ZADÁNÍ*` - okolo ní jsou mezery, takže pozor při parsování.

# Selenium
Jak jsem zmiňoval, tak tato stránka je ASP.NET forma... Tzn. že s ní nemůžeme nějak rozumně "ovládat" (tím myslím například poslat prostý POST request s třeba dvěma parametry). Proto jsem si přitáhl (a doufám, že vy taky) těžký kalibr - Selenium. Na této stránce chceme interakovat s přepínačem na zobrazení (ne)hotových úkolů, odesíláním úkolů a změnou stránky (popř. změnit velikost stránky). Pro přepínač na (ne)hotové úkoly můžeme použít XPath `//span[span/input[@id='cphmain_cbUnfinishedHomeworks_S']]`.


TODO: Napsat tohle nějak normálně a přehledně... Prostě nějak vhodně než sem jen fláknout informace (téměř) out-of-context... (Protože teď už přepisuji tuto celou dokumentaci o Bakalářích čtvrtý den a už mi z toho trochu hrabe... :) (a vážně se mi tu (teď) nechce rozepisovat o Seleniu a XPath).)



# Výzkum
Nalezeno přes proklik v menu. "Cesty" k elementům získány manuální analýzou HTML.