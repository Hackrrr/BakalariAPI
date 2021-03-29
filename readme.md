# BakalářiAPI

### Taky tě už štvou s něčím Bakaláři? Už sis někdy říkal(a), že snad nikdo nikdo nic horšího nevytvořil? A jseš tak trochu magor jako já? Tak zde je řešení - Oficiálně neoficiální API pro Bakaláře je tu! ~~Pouze za **99 Kč**.~~ A dokonce zadarmo!


Teď ale normálně...


Poznámka 0: Ty nadpisy jsou jen tak orientačně ("wait... oni jsou někdy nadpisy neorientační?") - Prakticky to tu píšu jako sloh, takže si stejně přečti vše :)


Poznámka 1: Předem omluva za můj projev - Spousta česglických frází a textů, můj pravopis, hromada emotů ( peepoHey ) a (asi to nejhorší) moje "vtipné" poznámky a můj styl humoru (ano, musel jsem napsat, že je to to nejhorší z toho všeho... :) )


Poznámka 2: A tedy se předem omlouvám za kvalitu celého totoho dokumentu (`Poznámky.md` jsou o něco "profesionálnější")


Poznámka 3: Víte jak jsem zmiňoval ten můj "humor"? Tak jsem tím myslel tohle :)


Poznámka 4: Yep - Toto... BTW Tyhle poznámky jsou actually úplně k ničemu (tedy jestli ti to ještě nedošlo)


# Co tohle je a proč by to někdo dělal?
`BakalářiAPI` (taky to budu nazívat bez diakritiky (`BakalariAPI`)) je můj projekt, který vznikl v době distanční výuky, jelikož ~~jsem se nudil a nebylo nic na práci~~ mě Bakaláři už delší dobu štvali - různý věci rozházený různě po stránkách, extrémně dlouhý načítání, nepřehlednost, nemožnost automatizace, ...
No a dopadlo to tak, že jsem začal psát tohle.


Nutno dodat, že název je takový sporný. Na jednu stranu název `BakalářiAPI` vypadá poměrně pěkně. Ovšem na druhou stranu to je spíše scraper než API. Ale na třetí stranu se z toho snažím udělat API. Takže tak.


A proč python? Protože jsem už delší dobu plánoval, že se na něj konečně kouknu... A nejlepší způsob, jak se kouknout na nějaký jazyk je udělat v něm extrémně velký projekt, který jste předtím nedělali ani v jiném, vám známem, jazyce :) .

# Je tohle pro mě?
Jak jsem již psal, tohle je snaha udělat nějaký přístupný API pro všechny. Pokud Python není problém a potřebujete/chcete získávat/získat nějaký data z Bakalářů, tak tohle je ideální. ~~Nevím o lepší řešení než je tento projekt (protože kdyby bylo nějaký lepší (resp. kdyby existovalo vůbec nějaký jiný (mimo nědělat to)), tak tohle nedělám).~~ (viz sekce *"Alternativy"*) Pokud jde o implementaci tohoto do ostatních jazyků - určitě existuje i ve tvém (ano! myslím tím tebe, čtenáři!) jazyce nějaký způsob, jak spustit Python script (ok, tedy mimo JS (pokud se nejedná o Node.js); musel jsem to napsat přestože JS je můj miláček widepeepoHappy ). Myslel jsem i na tohle a proto má `BakalářiAPI` tzn. `Looting`, což je část kódu (resp. třída) starající se o persistenci výsledků a lze tyto výsledky i exportovat. Zatím sice není moc kontrola nad tím, co a jak se vyexportuje, ale `Looting` nic neschovává (jakože ne že by v Pythonu moc mohl), takže pokud je zapotřebí jinej formát než je JSON (což je zatím jediný formát, který umí), tak není až tak složité napsat (nebo ukrandout ~~z netu~~ ze Stack Overflow) nějaký Python script na export do jiného formátu.


A pokud si chceš udělat vlastní `BakalářiAPI`, let's go for it. Tohle je Open Source, takže můžeš se podívat na kód, jak se řeší určitý věci a nebo se podívat do poznámek, co jsou tady taky - viz složka Bakaláři.

BTW - Co vím, tak minimální verze Pythonu je 3.7 (konkrétněji 3.7.0b1), protože `BakalářiAPI` používá anotace (z `__future__` modulu) (a na funkcionalitu, kterou toto poskytuje, tak jsem zvyklý z ostatních jazyků :) ). Ale samozřejmě je dost pravděpodobné, že se mýlím - Nezkoušel jsem předchozí verze, tudíž nevím, jestli to opravdu nefunguje a pokud z nějakého záhadného důvodu nechceš/nemůžeš použít novější Python, tak bych se i vsadil, že najdeš způsob, jak to zprovoznit.


**Ale neříkej, že jsem tě nevaroval - Je to extrémní pain.**

# Alternativy
Well... Když jsem tohle začínal, tak jsem prohledával internet a troufám si říct, že docela intenzivně... Ale přesto se zdá, že jsem něco přehlédl (přestože internet prohledávám prakticky pořád kvůli ostatním věcem). Tedy to, co jsem "přehlédl", jsem sice našel, ale neprozkoumal to pořádně - mám na mysli projekt/repozitář [`bakalari-api`](https://github.com/bakalari-api/bakalari-api) a s ním související (a to je to, čemu jsem nevěnoval pozornost). Tento repozitář samotný vypadal pěkně - dokumentace k reálným API  endpoitům Bakalářů... Jenže v době, kdy jsem tento repozitář "studoval", tak se tento repozitář zdál "mrtvý" (přestože tu byli relativně nedávné commity tak se nezdály relevantní). A vzhledem k tomu, že (má) škola přešla v té době (alespoň pro koncového "normálního" uživatele (ano, usuzuji pouze na základě změny UI, don't judge me :) )) na novou verzi, tak jsem tento repozitáž nechal. (Zdálo se, že je neaktuální + mé pokusy zreplikovat nějaké API dotazy nedopadly dobře (ale to bych spíše považoval za mojí blbost).)<br>
Avšak když jsem toto hledání po informacích opakoval (to jest doba, kdy jsem dokončil první "použitelnou" (tedy druhou) verzi shellu), tak jsem narazil na repozitář [`bakapi`](https://github.com/mvolfik/bakapi), který poskytoval (/poskytuje) nějaké funkce na vytažení dat z Bakalářů. Docela mě zarazilo, že tento repozitář je aktivní, tudíž jsem si ho zklonoval, vyzkoušel a k mému překvapení script fungoval. Po rychlé kontrole zdrojáku jsem zjistil, že používá `"/api/"` adresy, což (pro mě) byl docela zásadní objev, protože to znamená, že actually exituje "normální" (a oficiální) API pro Bakaláře (někde). Ok... Tak ale tohle nemohl "napsat z vody", right? Takže jsem se podíval na projekty/repozitáře autora a našel, že je členem [`bakalari-api`](https://github.com/bakalari-api) - a teď nemám na mysli repozitář, ale GitHub organizaci. A tato organizace má "pod sebou" repozitáž [`bakalari-api-v3`](https://github.com/bakalari-api/bakalari-api-v3), který obsahuje dokumentaci (současných (15. 11. 2020)) (fungujících) API endpointů. Co jsem z toho pobral, tak to berou z reverzování mobilní aplikace Bakalářů.


***A rád bych těm, co to spravůjí udělal nějaký shoutout za to, že to dělají.*** (Ano, tohle byl ten shoutout. :) )


Proč to jsem vůbec píšu? Protože proč ne? A budu rád, když alespoň jeden z projektů (ať už tento či nějaký z `bakalari-api`) bude funkční a použitelný - a čím víc uživatelů, tím to bude pravděpodobnější (I guess (tedy pokud někdo z oficiálních Bakalářů nepřijde na to, že tu jsou takovýhle projekty a nezačne to nějak řešit - sice jsem neodklikával žádne podmínky užívání, ale mám takové tušení, že by se jim to nemuselo líbit...)).


# Moje vyjádření k Bakalářům
Nic tu není... Jen nadpis... Proč? Protože to co tu původně bylo asi nebylo vhodné sem psát... Pokud to stejně chceš vidět, tak můžeš prohledat commity a najít, kdy to tu ještě bylo - já ti v tom bránit nebudu... A proč tu teda nechávám takovoutu referenci na něco, co vlastně tu ani být nemá? IDK... Já mám prostě rád takovéto "easter eggy"/zbytky minulosti - A tohle tu bylo téměř od začátku (což asi napoví, v jakých commitech hledat, pokud to chceš vědět) a často jsem tento "vzkaz" IRL referencoval (že jsem speciálně kvůli Bakalářům napsal něco takového :) ), tak mi přijde špatný to prostě vymazat... Prostě já LULW

# Co to (zatím) umí?
Získat informace o serveru (Verze/Evidenční číslo/Datum verze Bakalářů), online schůzekách, známkách a komens zprávách. Komens zprávy umí potvrdit a lze z nich stahovat přílohy. Dále `BakalářiAPI` umí získat seznam všech studentů, což si myslím, že by možný být němělo, ale je to tu... (Možná by se to mělo někomu nahlásit, ale eShrug.) A nakonec - `BakalářiAPI` automaticky shromažďuje výsledky (pokud se tato funkce nevypne). O to se stará (třída) `Looting`. Tyto výsledky lze pak exportovat do JSONu nebo je popř. i importovat.


Navíc je tu ještě `BakalářiAPI` shell (což je `main.py` soubor). Ten je oddělený a dá se považovat za ukázku toho, co `BakalářiAPI` umí.


#### Hlavní: ####
- Získat verzi Bakalářů (verze, evidenční číslo, datum verze)
- Získat online schůzky
- Získat seznam studentů na škole (nejspíše se leakuje omylem, takže očekávám, že tohle v nějaké další verzi Bakaláří znemožní)
- Získat známky
- Získat "nadcházející" úkoly (pouze se Seleniem)
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

# Zaujal jsem tě?
Ano? Tak to jsem rád... Smůla, že vůbec nevíš, jak tohle ~~použít~~ spustit... Ale zkus se podívat do "Dokumentace". :)