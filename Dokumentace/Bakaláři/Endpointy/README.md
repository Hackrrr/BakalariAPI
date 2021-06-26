# Endpointy
Zde jsou vypsány všechny URL adresy "endpointů", které `BakalářiAPI` používají. Vyskytuje se zde popis toho, co dělají, jak z nich získat to co chceme, ukázky requestů a responsů a třeba i jak to vypadá pro běžného uživatele, který si chce jen užít vynikající aplikace s názvem Bakaláři :).

# Struktura
Tohle je první větší dokumentace, kterou píši, takže nečekejte zázraky - vlastně první, která nemá jen jedno `README.md` KEKW Budu se snažit dodržet strukturu, ale tuším, že se to všude asi moc nepovede. Každopádně - každý endpoint by měl obsahovat následující věci (= většinou nadpisy):
- Cestu - První řádek, první nadpis; Reálná cesta k endpointu relativně k rootu Bakalářů
- Klíč - Druhý řádek; Klíč, který používá `BakalářiAPI` aby se nemusela používat reálná cesta; Shoduje se se jménem souboru (bez přípony)
- Metadata - Verze Bakalářů, když se dokument psal/upravoval + Datum verze Bakalářů, když se dokument psal/upravoval + Datum poslední úpravy dokumentu + Zda je doporučeno/potřeba použít Selenium (pozn.: Verze Bakalářů a datum úpravy se bude upravovat pouze pokud se změní informace/poznatky v daném dokumentu, resp. nezmění se, pokud se dokument bude pouze upraven v rámci překlepů nebo stylu)
- Přehled - Něco (málo/hodně) k tomu, co to je za endpoint, k čemu se nám hodí, co dělá a třeba to, jestli se k němu dostane normální uživatel, který nezkoumá zdrojový kód :)
- Request - Ukázka toho, co se na endpoint posílá
- Response - Ukázka toho, co se nám z endpointu vrací
- Výzkum - Jak se na endpoint přišlo a jak se přišlo na to, jak z něj získat data


Dále pak zde může být následující:
- Extrakce dat - X => Y – Popis extrakce/parsování dat
- Selenium - Jak můžeme výsledky vylepšit za pomoci Selenia

# Struktury odpovědí
Některé části Bakalářů vypadají jako reálné API a vrací normálně zpracovatelná data. Bohužel i tak se struktury odpovědí liší. Tyto jednotlivé struktury budou u určitých endpointů referencovány.

## Success JSON
Vyskytuje se napříč celými Bakaláři. Vypadá takto:
```json
{
    "success": true,
    "klíč `success`": "",
    "data": null
}
```
Oznamuje úspěšnost dotazu (klíč `success`), případně vrácená data (klíč `data`). Zatím nebyl nalezen případ, kdy klíč `error` má jinou hodnotu než `""`.
## Error JSON
Byl zpozorován u Komens endpointů. Statusový kód HTTP, pokud se vrátí tento JSON, je 500 (Internal Server Error). Jeho struktura je následující:
```json
{
    "Message": "Při zpracování požadavku došlo k chybě.",
    "StackTrace": "",
    "ExceptionType": ""
}
```
Klíče `StackTrace` a `ExceptionType` byly vždy zpozorovány jako `""`. Klíč `Message` má očividně vždy stejnou zprávu, avšak tato zpráva je lokalizovaná - V angličtině a vietnamštině je zde `"There was an error processing the request."`.

# Poznámky
- Pokud se objeví něco ve smyslu "pro normální uživatele nedostupný", tak je tím na mysli to, že normální uživatel nezaregistruje, že tu něco jako takového je, tzn. žádná interakce
- Formát `*NĚJAKÁ_HODNOTA*`, tedy ohraničena hvězdičkami, velkými písmeny, bez mezer, s diakritikou, je použit pro důležité hodnoty, které se mění či se mají dosadit
- Pokud se zmiňuje určitá hodnota, tak je obalena v markdownu v backtickách, tedy je formátovaná `takto`
- Některá data mohou být lokalizovaná. Tzn., že se data liší v závislosti na vybraném jazyku v nastavení účtu Bakalářů.
- Uvedená ID nemusejí být reálná ID - Nevím, co vše se může získat za pomocí nějakých ID a proto je pro jistotu měním, ale všechna uvedená ID by teoreticky mohla existovat. (Pokud zde není generování ID tak, že musí sedět nějaký kontrolní součet a obsahovat 3 určitá písmena, tak si myslím, že by měli všechny ID být validní.)

# Problémy
- Bakaláři jsou očividně citlivý na správný `content-type` header (= header v requestu, který určuje typ zaslaných dat). Pokud tedy endpoint očekává JSON data, je potřeba mít přítomný tento header v requestu: `Content-Type: application/json`
