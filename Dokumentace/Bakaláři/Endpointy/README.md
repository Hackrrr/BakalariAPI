# Endpoity
Zde jsou vypsány všechny URL adresy "endpointů", které `BakalářiAPI` používají. Vyskytuje se zde popis toho, co dělají, jak z nich získat to co chceme, ukázky requestů a responsů a třeba i jak to vypadá pro běžného uživatele, který si chce jen užít vynikající aplikace s názvem Bakaláři :).

# Struktura
Tohle je prnví větší dokumentace kterou píšu, takže nečekejte zázraky... (actually prní, která nemá jen jedno `README.md` KEKW ) Snažím se/snažil jsem se dodržovat nějakou strukturu, ale tuším, že se to všude asi moc nepovedlo... Každopádně - každý endpoint by měl obsahovat následující věci (= většinou nadpisy):
- Cestu - První řádek, první nadpis; Reálná cesta k endpointu relativně k root Bakalářů
- Klíč - Druhý řádek; Klíč, který používajá `BakalářiAPI` aby se nemusela používat reálná cesta; Shoduje se s jménem souboru (bez přípony)
- Metadata - Verze Bakalářů, když se dokument psal/upravoval + Datum verze Bakalářů, když se dokument psal/upravoval + Datum poslední úpravy dokumentu + Jesli je doporučeno/potřeba použít Selenium
- Přehled - Něco (málo/hodně) k tomu, co to je za endpoint, k čemu se nám hodí, co dělá a třeba to, jestli se k němu dostane normální uživatel, který nezkoumá zdroják :)
- Request - Ukázka toho, co se na endpoint posílá
- Response - Ukázka toho, co se nám z endpointu vrací
- Výzkum - Jak se na endpoint přišlo a jak se přišlo na to, jak zněj získat data


Dále pak zde může být následující:
- Extrakce dat - X => Y - Ukazuje, jak se data parsují, aby jsme dostali to co chceme
- Selenium - Jak můžeme výsledky vylepšit za pomoci Selenia

# Poznámky
- Pokud se objeví něco ve smyslu "pro normální uživatele nedostupný", tak je tím na mysli to, že normální uživatel nezaregistruje, že tu něco jako takového je, tzn. žádná interakce
- Formát `*NĚJAKÁ_HODNOTA*`, tedy ohraničena hvězidčkami, velkými písmeny, bez mezer, s diakritikou, je použit pro důležité hodnoty, které se mění či se mají dosadit
- Pokud se zmiňuje určitá hodnota, tak je obalena v markdownu v backtickách, tedy je formátovaná `takto`
- U určitých endpointů, kdy se jedná o "reálné" a normální API, které vrací JSON se může objevit něco ve smyslu, že se nám vrací "klasicky zabalená data". Tím jsou na mysli klasicky zabalená data (pouze) v rámci Bakalářů. Klasicky zabalená data vypadají takto: `{"success":true,"error":"","data":null}` - Indikuje úspěšnost požadavku a obsahuje případná data nebo případně chybovou hlášku
- Uvedená IDčka nemusejí být reálná ID - Nevím, co vše se může získat za pomocí nějakých ID a proto je pro jistotu měním, ale všechna uvedená ID by teoreticky mohla existovat. (Pokud zde není generování IDček tak, že musí sedět nějaký kontrolní součet a obsahovat 3 určitá písmena, tak si myslím, že by měli všechny ID být validní.)