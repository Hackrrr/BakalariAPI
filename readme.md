# BakalářiAPI

### Taky tě už štvou s něčím Bakaláři? Už sis někdy říkal(a), že snad nikdo nikdo nic horšího nevytvořil? A jseš tak trochu magor jako já? Tak zde je řešení - Oficiálně neoficiální API pro Bakaláře je tu! ~~Pouze za **99 Kč**.~~ A dokonce zadarmo!

<br>

Teď ale normálně... 

# Co tohle je a proč by to někdo dělal?
`BakalářiAPI` (často ho taky budu nazívat bez diakritiky (`BakalariAPI`)) je můj projekt, který vznikl v době distanční výuky, jelikož ~~jsem se nudil a nebylo nic na práci~~ mě Bakaláři už delěí dobu štvali - různý věci rozházený různě po stránkách, extrémně dlouhý načítání, nepřehlednost, ...
No a dopadlo to tak, že jsem začal psát tohle.
<br>
Nutno dodat, že název je takový sporný. Na jednu stranu název `BakalářiAPI` vypadá poměrně pěkně. Ovšem na druhou stranu to je spíše scraper než API. Ale na třetí stranu se z toho snažím udělat API. Takže tak.
<br>
A proč python? Protože jsem už delší dobu plánoval, že se na něj konečně kouknu... A nejlepší způsob, jak se kouknout na nějaký jazyk je udělat v něm extrémně velký projekt, který jste předtím nedělali ani v jiném, vám známem, jazyce **:)**.

# Je tohle pro mě?
Jak jsem již psal, tohle je snaha udělat nějaký přístupný API pro všechny. Pokud Python není problém a potřebujete/chcete získávat/získat nějaký data z Bakalářů, tak tohle je ideální. Nevím o lepší řešení než je tento projekt (protože kdyby bylo nějaký lepší (resp. kdyby existovalo vůbec nějaký jiný (mimo nědělat to)), tak tohle nedělám). Pokud jde o implementaci tohoto do ostatních jazyků - určitě existuje i ve tvém (ano! myslím tím tebe, čtenáři!) jazyce nějaký způsob, jak spustit Python script. Myslel jsem i na tohle a proto má `BakalářiAPI` tzn. `Looting`, což je část kódu (resp. třída) starající se o persistenci výsledků a lze tyto výsledky i exportovat. Zatím sice není moc kontrola nad tím, co všechno se vyexportuje, ale `Looting` nic neschovává, takže pokud je zapotřebí jinej formát než je JSON (což je zatím jediný formát, který to umí), tak není až tak složité napsat nějaký Python script na export do jiného formátu.<br>
A pokud si chceš udělat vlastní `BakalářiAPI`, let's go for it. Tohle je Open Source, takže můžeš se podívat na kód, jak se řeší určitý věci a nebo se podívat do poznámek, co jsou tady taky (`"Poznámky.md"`).
**Ale neříkej, že jsem tě nevaroval - Je to extrémní pain (viz mé vyjádření v poznámkách).**

# Co to (zatím) umí?
Získat informace o serveru (Verze/Evidenční číslo/Datum verze Bakalářů), online schůzekách, známkách a komens zprávách. Komens zprávy umí potvrdit a lze z nich stahovat přílohy. Dále `BakalářiAPI` umí získat seznam všech studentů, což si myslím, že by možný být němělo, ale je to tu... (Možná by se to mělo někomu nahlásit, ale eShrug.) A nakonec - `BakalářiAPI` automaticky shromažďuje výsledky (pokud se tato funkce nevypne). O to se stará (třída) `Looting`. Tyto výsledky lze pak exportovat do JSONu nebo je popř. i importovat.<br>
Navíc je tu ještě `BakalářiAPI` shell. Ta je oddělená a dá se považovat za ukázku toho, co `BakalářiAPI` umí.

# Instalace/Zprovoznění
`BakalářiAPI` je Pythonu 3. Pokud nemáte Python, tak si ho buď nainstaluj (prostě to udělel LOL Čtyřhlav) nebo na tohle zapomeň. Nemyslím to ve zlém, ale já jsem rád, že jsem tohle vůbec udělal natož tohle přepisovat do jiného jazyka.(Pokud ale přesto chceš jiný jazyk jak Python => viz 2. odstavec sekce *Je tohle pro mě?*.)<br>
Pokud je Python 3 dostupný (pravděpodobně i s menšími úpravami Python 2 (ale *proč?!*, když už je EOL)), tak potřebujeme následující moduly/balíčky: `requests` a `BeatifulSoup4` (zkráceně `bs4`). Pro jejich instalaci využij `pip`:
```
pip install requests bs4
```
And here we go! Nyní stačí jen importovat `BakalariAPI` a můžeme začít získávat data!

# Použití