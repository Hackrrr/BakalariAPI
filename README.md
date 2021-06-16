# BakalářiAPI

### Taky tě už štvou s něčím Bakaláři? Už sis někdy říkal(a), že snad nikdo nikdy nic horšího nevytvořil? A seš tak trochu magor jako já? Tak zde je řešení - Oficiálně neoficiální API pro Bakaláře je tu! ~~Pouze za **99 Kč**.~~ A dokonce zadarmo!

Teď ale normálně...

Poznámka 0: Ty nadpisy jsou jen tak orientačně ("wait... oni jsou někdy nadpisy neorientační?") - Prakticky to tu píšu jako sloh, takže si stejně přečti vše :)

Poznámka 1: Předem omluva za můj projev - Spousta česglických frází a textů, můj pravopis, hromada emotů (peepoHey) a (asi to nejhorší) moje "vtipné" poznámky a můj styl humoru

Poznámka 2: A tedy se předem omlouvám za kvalitu celého tohoto dokumentu (složka "Dokumentace/" je o něco "profesionálnější")

Poznámka 3: Víte, jak jsem zmiňoval ten můj "humor"? Tak jsem tím myslel tohle :)

Poznámka 4: Yep - Toto... BTW Tyhle poznámky jsou actually úplně k ničemu (tedy jestli ti to ještě nedošlo)

# Co tohle je a proč by to někdo dělal?
`BakalářiAPI` (taky to budu nazývat bez diakritiky (`BakalariAPI`)) je můj projekt, který vznikl v době distanční výuky, jelikož ~~jsem se nudil a nebylo nic na práci~~ mě Bakaláři už delší dobu štvali - různý věci rozházený různě po stránkách, extrémně dlouhý načítání, nepřehlednost, nemožnost automatizace, ...
No a dopadlo to tak, že jsem začal psát tohle.

Nutno dodat, že název je takový sporný. Na jednu stranu název `BakalářiAPI` vypadá poměrně pěkně. Ovšem na druhou stranu to je spíše scraper než API. Ale na třetí stranu se z toho snažím udělat API. Takže tak.

A proč python? Protože jsem už delší dobu plánoval, že se na něj konečně kouknu... A nejlepší způsob, jak se kouknout na nějaký jazyk je udělat v něm extrémně velký projekt, který jste předtím nedělali ani v jiném, vám známém, jazyce :) .

# Je tohle pro mě?
Jak jsem již psal, tohle je snaha udělat nějaký přístupný API pro všechny. Pokud Python není problém a potřebuješ/chceš získávat/získat nějaký data z Bakalářů, tak tohle je ideální. ~~Nevím o lepší řešení než je tento projekt (protože kdyby bylo nějaký lepší (resp. kdyby existovalo vůbec nějaký jiný řešení (mimo nedělat to)), tak tohle nedělám).~~ (Oprava - K tomuto jsem se rozepsal v sekci *"Alternativy"*.)

Pokud nemáš z nějakého záhadného důvodu možnost psát Python kód (třeba že si líný/líná se ho naučit) a jde ti o implementaci tohoto do ostatních jazyků - určitě existuje i ve tvém jazyce (Ano! Myslím tím tebe, čtenáři!) nějaký způsob, jak spustit Python (ok, tedy mimo JS, pokud se nejedná o Node.js). Myslel jsem i na tohle a proto má `BakalářiAPI` tzv. `Looting`, což je část kódu (resp. třída) starající se o persistenci výsledků a tyto výsledky lze i exportovat. Zatím sice není moc kontrola nad tím, co a jak se vyexportuje, ale `Looting` nic neschovává (jakože ne že by v Pythonu moc mohl), takže pokud je zapotřebí jiný formát než je JSON (což je zatím jediný formát, který umí), tak není až tak složité napsat (nebo ~~ukradnout~~ vypůjčit si ~~z netu~~ ze Stack Overflow) nějaký Python skript na převod dat do jiného formátu.

A pokud si chceš udělat vlastní `BakalářiAPI`, go for it. Tohle je open source, takže můžeš se podívat na kód, jak se řeší určitý věci anebo se podívat do poznámek, co jsou tady taky - viz složka "Dokumentace". A nebo si klidně celý projket forkni a pracuj na svém.

# Kompatibilita
Oficiálně tohle funguje na Windowsech na Python verzi 3.9. Není mi známo, jestli bude fungovat na jichý verzích nebo na jiných OS (starší verze projektu jsem rozchodil jak na Linuxu tak na Androidu (Termux) (tzn. Linux v trochu jiném kabátku), ale nový jsem nezkoušel). Spíš než Python bude problém Selenium (viz dále [zde](Dokumentace/readme.md).

Co vím, tak minimální verze Pythonu je 3.9, protože `BakalářiAPI` používá určité věci, které jsem líný psát jinak (teď si nevzpomenu, co je ta jedna věc, kvůli které by to měla být alespoň verze 3.9, ale minimálně anotace (které `BakalářiAPI` používá) jsou až od verze 3.7). Ale samozřejmě je dost pravděpodobné, že se pletu - Nezkoušel jsem předchozí verze, tudíž nevím, jestli to opravdu nefunguje a pokud z nějakého záhadného důvodu nechceš/nemůžeš použít novější Python, tak bych se i vsadil, že najdeš způsob, jak to zprovoznit.

# Alternativy
Well... Když jsem tohle začínal, tak jsem prohledával internet a troufám si říct, že docela intenzivně... Ale přesto se zdá, že jsem něco přehlédl (přestože internet prohledávám prakticky pořád kvůli ostatním věcem). To co jsem "přehlédl", jsem sice našel, ale neprozkoumal to pořádně - mám na mysli projekt/repozitář [`bakalari-api`](https://github.com/bakalari-api/bakalari-api) a s ním související (a to je to, čemu jsem nevěnoval pozornost). Tento repozitář samotný vypadal pěkně - dokumentace k reálným API endpoitům Bakalářů... Jenže v době, kdy jsem tento repozitář "studoval", tak se tento repozitář zdál "mrtvý" (přestože tu byli relativně nedávné commity tak se nezdály relevantní). A vzhledem k tomu, že (má) škola přešla v té době (alespoň pro koncového "normálního" uživatele (ano, usuzuji pouze na základě změny UI, don't judge me :) )) na novou verzi, tak jsem tento repozitář nechal na pokoji. (Zdálo se, že je neaktuální + mé pokusy zreplikovat nějaké API dotazy nedopadly dobře (ale to bych spíše považoval za mojí blbost).)

Avšak když jsem toto hledání po informacích opakoval (to jest doba, kdy jsem dokončil první "použitelnou" (tedy druhou) verzi shellu), tak jsem narazil na repozitář [`bakapi`](https://github.com/mvolfik/bakapi), který poskytoval (/poskytuje) nějaké funkce na vytažení dat z Bakalářů. Docela mě zarazilo, že tento repozitář je aktivní, tudíž jsem si ho zklonoval, vyzkoušel a k mému překvapení script fungoval. Po rychlé kontrole zdrojáku jsem zjistil, že používá `"/api/"` adresy, což (pro mě) byl docela zásadní objev, protože to znamená, že actually existuje "normální" (a oficiální) API pro Bakaláře (někde). A řekl jsem si: "Ok... Tak ale tohle nemohl "napsat z vody", right? Pokud to tedy není úplný magor jako já PepeLaugh ..." Takže jsem se podíval na projekty/repozitáře autora a našel, že je členem [`bakalari-api`](https://github.com/bakalari-api) - a teď nemám na mysli repozitář, ale GitHub organizaci. A tato organizace má "pod sebou" repozitář [`bakalari-api-v3`](https://github.com/bakalari-api/bakalari-api-v3), který obsahuje dokumentaci (fungujících) API endpointů. Co jsem z toho pobral, tak to berou z reverzování mobilní aplikace Bakalářů.

Proč to sem vůbec píšu? Protože proč ne? Alespoň trochu proma pro ně od neznámeho človíčka na internetu :).

# Moje vyjádření k Bakalářům
Nic tu není... Jen nadpis... Proč? Protože to co tu původně bylo asi nebylo vhodné sem psát... Pokud to stejně chceš vidět, tak můžeš prohledat commity a najít, kdy to tu ještě bylo - já ti v tom bránit nebudu... A proč tu teda nechávám takovouto referenci na něco, co vlastně tu ani být nemá? IDK... Já mám prostě rád takovéto "easter eggy"/zbytky minulosti - A tohle tu bylo téměř od začátku, takže mi přijde špatný to prostě vymazat... Prostě já. LULW

# Co to (zatím) umí?
Samotné `BakalářiAPI` umí (v tuto chvíli) zjistit informace o samotný Bakalářích (verze, evidenční číslo, ...) a nějaké metadata o uživatelovi (např. hash, který netuším, k čemu slouží) a vytáhnout z Bakalářů úkoly, schůzky, Komens zprávy a známky - samozřejmě jen to co uvidíte normálně, když se přihlásíte (tedy nemůžete se podívat např. na zprávy ostatních :) ). Docela zajímavé je to, že jsem byl schopný najít způsob, jak vytáhnout seznam všech studentů, takže dokáže i toto :). (Pokud tě zajímá jak jsem to dokázal, podívej se do poznámek k ["meetings_overview"](/Dokumentace/Bakaláři/Endpointy/meetings_overview.md) endpointu.)

Dále je tu již zmiňovaná `Looting` třída, která má na starosti záznam a export/import získaných výsledků.

Navíc je tu ještě `bakalarishell` modul/příkaz. Ten je oddělený a dá se považovat za ukázku toho, co `BakalářiAPI` umí.

Jinak celý výčet funkcí je zde:
#### Hlavní: ####
- Získat informace o systému Bakaláři (verze, evidenční číslo, datum verze)
- Získat online schůzky
- Získat seznam studentů na škole (nejspíše se leakuje omylem, takže očekávám, že tohle v nějaké další verzi Bakaláři znemožní)
- Získat známky
- Získat úkoly (se Seleniem všechny, bez něj je toto limitované na prvních 20 nehotových aktivních úkolů)
- Označení úkolu jako hotový
- Získat komens zprávy
- Potvrdit komens zprávy
- Stahovat soubory (přílohy komens zpráv a úkolů)
- Export/Import dat
#### Funkcionalita `bakalarishell` (= ukázka, co se s něčím jako `BakalářiAPI` dá dělat): ####
- Uživatelský shell na získání a zobrazení dat
- Připojení k (blízkým) nadcházejícím schůzkám
- Barvičky peepoHappy
- Potvrzení nehotových úkolů a přečtení zpráv
- Import/Export dat ze/do souboru

# Zaujal jsem tě?
Ano? Tak to jsem rád... Smůla, že vůbec nevíš, jak tohle ~~použít~~ spustit (i když to nejspíš dokážeš)... Ale zkus se podívat [sem](/Dokumentace/README.md), kde je to trochu techničtější a je tam ještě mnohem víc textu, se kterým můžeš zabít nějaký ten čas. :)