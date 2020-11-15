# BakalářiAPI

### Taky tě už štvou s něčím Bakaláři? Už sis někdy říkal(a), že snad nikdo nikdo nic horšího nevytvořil? A jseš tak trochu magor jako já? Tak zde je řešení - Oficiálně neoficiální API pro Bakaláře je tu! ~~Pouze za **99 Kč**.~~ A dokonce zadarmo!

<br>
Teď ale normálně...
<br>
Poznámka 0: Ty nadpisy jsou jen tak orientačně ("wait... oni jsou někdy nadpisy neorientační?") - Prakticky to tu píšu jako sloh, takže si stejně přečti vše :)<br>
Poznámka 1: Předem omluva za můj projev - Spousta česglických frází a textů, můj pravopis, hromada emotů ( peepoHey ) a (asi to nejhorší) moje "vtipné" poznámky a můj styl humoru (ano, musel jsem napsat, že je to to nejhorší z toho všeho... :) )<br>
Poznámka 2: A tedy se předem omlouvám za kvalitu celého totoho dokumentu (`Poznámky.md` jsou o něco "profesionálnější")<br>
Poznámka 3: Víte jak jsem zmiňoval ten můj "humor"? Tak jsem tím myslel tohle :)<br>
Poznámka 4: Yep - Toto... BTW Tyhle poznámky jsou actually úplně k ničemu (tedy jestli ti to ještě nedošlo)<br>

# Co tohle je a proč by to někdo dělal?
`BakalářiAPI` (často ho taky budu nazívat bez diakritiky (`BakalariAPI`)) je můj projekt, který vznikl v době distanční výuky, jelikož ~~jsem se nudil a nebylo nic na práci~~ mě Bakaláři už delší dobu štvali - různý věci rozházený různě po stránkách, extrémně dlouhý načítání, nepřehlednost, nemožnost automatizace, ...
No a dopadlo to tak, že jsem začal psát tohle.
<br>
Nutno dodat, že název je takový sporný. Na jednu stranu název `BakalářiAPI` vypadá poměrně pěkně. Ovšem na druhou stranu to je spíše scraper než API. Ale na třetí stranu se z toho snažím udělat API. Takže tak.
<br>
A proč python? Protože jsem už delší dobu plánoval, že se na něj konečně kouknu... A nejlepší způsob, jak se kouknout na nějaký jazyk je udělat v něm extrémně velký projekt, který jste předtím nedělali ani v jiném, vám známem, jazyce **:)**.

# Je tohle pro mě?
Jak jsem již psal, tohle je snaha udělat nějaký přístupný API pro všechny. Pokud Python není problém a potřebujete/chcete získávat/získat nějaký data z Bakalářů, tak tohle je ideální. ~~Nevím o lepší řešení než je tento projekt (protože kdyby bylo nějaký lepší (resp. kdyby existovalo vůbec nějaký jiný (mimo nědělat to)), tak tohle nedělám)~~ (viz sekce *"Alternativy"*). Pokud jde o implementaci tohoto do ostatních jazyků - určitě existuje i ve tvém (ano! myslím tím tebe, čtenáři!) jazyce nějaký způsob, jak spustit Python script (ok, tedy mimo JS; musel jsem to napsat přesotže JS je můj miláček widepeepoHappy). Myslel jsem i na tohle a proto má `BakalářiAPI` tzn. `Looting`, což je část kódu (resp. třída) starající se o persistenci výsledků a lze tyto výsledky i exportovat. Zatím sice není moc kontrola nad tím, co a jak se vyexportuje, ale `Looting` nic neschovává (jakože ne že by v Pythonu moc mohl), takže pokud je zapotřebí jinej formát než je JSON (což je zatím jediný formát, který umí), tak není až tak složité napsat nějaký Python script na export do jiného formátu.<br>
A pokud si chceš udělat vlastní `BakalářiAPI`, let's go for it. Tohle je Open Source, takže můžeš se podívat na kód, jak se řeší určitý věci a nebo se podívat do poznámek, co jsou tady taky (`"Poznámky.md"`).
**Ale neříkej, že jsem tě nevaroval - Je to extrémní pain (viz *"Moje vyjádření k Bakalářům"*).**

# Alternativy
Well... Když jsem tohle začínal, tak jsem prohledával internet a troufám si říct, že docela intenzivně... Ale přesto se zdá, že jsem něco přehlédl (přestože internet prohledávám prakticky pořád kvůli ostatním věcem). Tedy to, co jsem "přehlédl", jsem sice našel, ale neprozkoumal to pořádně - mám na mysli projekt/repozitář [`bakalari-api`](https://github.com/bakalari-api/bakalari-api) a s ním související (a to je to, čemu jsem nevěnoval pozornost). Tento repozitář samotný vypadal pěkně - dokumentace k reálným API  endpoitům Bakalářů... Jenže v době, kdy jsem tento repozitář "studoval", tak se tento repozitář zdál "mrtvý" (přestože tu byli relativně nedávné commity tak se nezdály relevantní). A vzhledem k tomu, že (má) škola přešla v té době (alespoň pro koncového "normálního" uživatele (ano, usuzuji pouze na základě změny UI, don't judge me :) )) na novou verzi, tak jsem tento repozitáž nechal. (Zdálo se, že je neaktuální + mé pokusy zreplikovat nějaké API dotazy nedopadly dobře (ale to bych spíše považoval za mojí blbost).)<br>
Avšak když jsem toto hledání po informacích opakoval (to jest doba, kdy jsem dokončil první "použitelnou" (tedy druhou) verzi shellu), tak jsem narazil na repozitář [`bakapi`](https://github.com/mvolfik/bakapi), který poskytoval (/poskytuje) nějaké funkce na vytažení dat z Bakalářů. Docela mě zarazilo, že tento repozitář je aktivní, tudíž jsem si ho zklonoval, vyzkoušel a k mému překvapení script fungoval. Po rychlé kontrole zdrojáku jsem zjistil, že používá `"/api/"` adresy, což (pro mě) byl docela zásadní objev, protože to znamená, že actually exituje "normální" (a oficiální) API pro Bakaláře (někde). Ok... Tak ale tohle nemohl "napsat z vody", right? Takže jsem se podíval na projekty/repozitáře autora a našel, že je členem [`bakalari-api`](https://github.com/bakalari-api) - a teď nemám na mysli repozitář, ale GitHub organizaci. A tato organizace má "pod sebou" repozitáž [`bakalari-api-v3`](https://github.com/bakalari-api/bakalari-api-v3), který obsahuje dokumentaci (současných (15. 11. 2020)) (fungujících) API endpointů. Co jsem z toho pobral, tak to berou z reverzování mobilní aplikace Bakalářů.
<br>
***A rád bych těm, co to spravůjí udělal nějaký shoutout za to, že to dělají.*** (Ano, tohle byl ten shoutout. :) )
<br>
Proč to jsem vůbec píšu? Protože proč ne? A budu rád, když alespoň jeden z projektů (ať už tento či nějaký z `bakalari-api`) bude funkční a použitelný - a čím víc uživatelů, tím to bude pravděpodobnější (I guess (tedy pokud někdo z oficiálních Bakalářů nepřijde na to, že tu jsou takovýhle projekty a nezačne to řešit)).

# Moje vyjádření k Bakalářům
Za tu dobu, co se vrtám v IT jsem toho viděl už relativně dost. A zcela určitě můžu prohlásit, že Bakaláři je snad to nejhorší co jsem viděl... Jen se podívejte na to, co za prasárny se tam děje... Vypadá to jak kdyby to dělalo 30 lidí, každý měl jinou představu, jak by to mělo fungovat a tak to udělal každý po svém. 80% věcí je dělaných jedním způsobem, dalších 75% jiným, následujících 60% je něco mezitím a těch zbylích 30% je každý nějak jinak. Nehledě na to, že referencujou snad všechny knihovny, co našli... Jediný co se dá na Bakalářích pochválit je design (což je (na jejich obranu) actually asi jedniná věc o kterou se koncový uživatel stará). Ok, dokážu přehlédnout neexistenci "normálního" API - třeba to chtěli udělat těžší pro ty, co to budou revesovat (a stejně tu jsou určitý věci přes API)... Ale prostě... Dám příklad úkolů (což je asi největší prasárna ze všech):<br>
Pomineme první načtení (na to nemám nervy rozepisovat)... Když chcete změnit velikost stránky, tak se pošle request s doslova víc jak 10ti hodnotama, znichž většina z jich jsou doslova statická data, vrátí se JSON, který má v sobě HTML, které se vloží na stránku a toto HTML spustí JS (protože má v sobě asi 6 `<script>` tagů), které vezmou to HTML, přetransformujou ho a přemístí... Můžemi někdo prosím vysvětlit, proč?! Proč by někdo dělal něco takovýho?! Ok, uvažujme to, že jsme to nějak střebali, teď už tu nic hrozného ne- Je. Tohle se stane, když chcete zobrazit víc výsledků na stránce, ale když chcete zobrazit další stránku, tak se stránka načte znovu... Jo to zní jednodušeji, **ale proč by to někdo dělal, když už tu je ta druhá cesta, která už je hotová, (bohužel) funguje?!** (BTW tohle je jen jeden způsob, jak je nějaká věc na Bakalářích udělaná.)
<br>
(Poznámka od současného já pro moje minulé já (a ostatní): Zdravím moje minulé já! To na co si stěžuješ jsou ASP.NET formy. Přeji hezký den :).)
<br>
Tak toto bylo moje vyjádření k Bakalářům :)

# Co to (zatím) umí?
Získat informace o serveru (Verze/Evidenční číslo/Datum verze Bakalářů), online schůzekách, známkách a komens zprávách. Komens zprávy umí potvrdit a lze z nich stahovat přílohy. Dále `BakalářiAPI` umí získat seznam všech studentů, což si myslím, že by možný být němělo, ale je to tu... (Možná by se to mělo někomu nahlásit, ale eShrug.) A nakonec - `BakalářiAPI` automaticky shromažďuje výsledky (pokud se tato funkce nevypne). O to se stará (třída) `Looting`. Tyto výsledky lze pak exportovat do JSONu nebo je popř. i importovat.<br>
Navíc je tu ještě `BakalářiAPI` shell (což je `main.py` soubor). Ten je oddělený a dá se považovat za ukázku toho, co `BakalářiAPI` umí.
<br>
#### Hlavní: ####
- Získat verzi Bakalářů (verze, evidenční číslo, datum verze)
- Získat online schůzky
- Získat seznam studentů na škole (nejspíše se leakuje omylem, takže očekávám, že tohle v nějaké další verzi Bakaláří znemožní)
- Získat známky
- Získat komens zprávy
- Potvrdit komens zprávy
- Stahovat přílohy komens zprávám
- Export/Import dat (pomocí classy `Looting`)
#### Fungující ale... ale (experimentální I guess): ####
- Získání seznamu IDček domácích úkolů (ano, pouze ID (nová cesta, jak je získat od verze Bakalářů `1.35.1023.2`))
- Označení úkolu jako hotový (podle ID)
#### Funkce `main.py` (= ukázka, co se s něčím takovýmhle dá dělat): ####
- Uživatelký shell na získání a zobrazení dat (komens, schůzky, známky, ... (prostě to co samotný `BakalariAPI` zatím umí))
- Připojení k (blízkým) nadcházejícím schůzkám


# Instalace/Zprovoznění
`BakalářiAPI` bylo psáno v Pythonu 3.9 (nevím, ale nejspíše funguje na většinu 3.x verzí). Pokud nemáte Python, tak si ho buď nainstaluj (prostě to udělel LOL Čtyřhlav) nebo na tohle zapomeň. Nemyslím to ve zlém, ale já jsem rád, že jsem tohle vůbec udělal, natož tohle přepisovat do jiného jazyka. (Pokud ale přesto chceš jiný jazyk jak Python => viz 2. odstavec sekce *"Je tohle pro mě?"*.)<br>
Pokud je Python 3 dostupný (pravděpodobně i s menšími úpravami Python 2 (ale *proč?!*, když už je EOL)), tak potřebujeme následující moduly/balíčky: `requests` a `BeatifulSoup4` (zkráceně `bs4`). Pro jejich instalaci využij `pip`:
```
pip install requests bs4
```
And here we go! Nyní stačí jen importovat `BakalariAPI` a můžeme začít získávat data!

# Použití
