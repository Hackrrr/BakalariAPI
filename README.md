# BakalářiAPI
`BakalářiAPI` je osobní projekt v Pythonu, který se snaží vytvořit jednoduchý způsob, jak pracovat s Bakaláři.

# Status
Přestože je aktuální verze `4.0`, `BakalářiAPI` se pořád často a poměrně drasticky mění. "Veřejná" část API tomuto nepodléhá, ale interní věci se mění prakticky neustále, a pokud je někdo užije, měl by mít na paměti, že je dost pravděpodobně, že v další verzi `BakalářiAPI` to nebude fungovat stejně. Jinak řečeno - prakticky každá verze je major, tzn., že pravděpodobně rozbije aplikace postavené na předchozí verzi.

# Jak to funguje a co to umí?
Je to jednoduché - tváříme jako "normální" uživatel, který využívá webové rozhraní aplikace Bakaláři a při tom si zapisuje vše podstatné. Většinu dokážeme udělat jen z prostých dotazů, jejichž výsledek následně zpracujeme, avšak jelikož Bakaláři využívají ASP.NET forms, tak jsou zde určité situace, kdy nelze jednoduše udělat dotaz vytvořit a pro takové situace se pokusí `BakalářiAPI` použít Selenium (pokud je nastaveno).

Ačkoli původně šlo jen o vytvoření základního API, projekt postupně expandoval a nyní bych to označil za několik věcí v sobě, jehož hlavní části jsou `bakalariapi` (samotné API pro Bakaláře) a `bakalarishell` (konzolová aplikace pro základní práci s Bakaláři). V budoucnu se tyto věci pravděpodobně rozdělí, ale zatím jsou spolu.

# Instalace
Instalaci lze provést přes `pip`:
```
pip install bakalariapi
```
Tím se nainstaluje poslední verze `BakalářiAPI`. Pokud chceš vyzkoušet všecny novinky, co se ještě nedostali do žádné verze, můžeš `BakalářiAPI` nainstalovat přímo ze zdroje (doufám, že není nutno dodávat, že `BakalářiAPI` může být a pravděpodobně bude značně nestabilní):
```
pip install git+https://github.com/Hackrrr/BakalariAPI
```
Nyní lze importovat modul `bakalariapi` a lze spustit shell přes příkaz `bakalarishell`. Většina funkcí by měla fungovat, ale pro další funkcionalitu je potřeba nastavit Selenium.

# Selenium
Jak bylo zmíněno, Bakaláři využívají ASP.NET formuláře. Naštěstí se většinou dají obejít, ale pro některé věci je potřebujeme. A náš (ne až tak moc) vražedný nástroj na tyto formuláře je Selenium.

Nejdříve WebDriver. WebDriver je technologie, která umožňuje ovládat prohlížeč vzdáleně, například "klikni sem", "napiš tohle", "dej mi současné cookies" a další. Problém je, že WebDriver je většinou další program, mimo samotný prohlížeč a který se pro každý prohlížeč liší, tzn. jiný pro Chrome a pro Firefox. Abychom tedy mohli této technologie využít, potřebujeme stáhnout správný webdriver.

Nyní Selenium. Selenium je wrapper kolem WebDriveru. Dělá nám ~~pěkné~~ API k webdriveru, abychom nemuseli řešit "low-level" záležitosti (které jsou definované ve WebDriver standardu) a mohli volat jen nějakou funkci.

A nakonec - proč tohle vůbec potřebujeme? Tak jak je napsáno výše, sestavit dotaz na ASP.NET formuláře není nejjednodušší, a proto takovéto dotazy doslova simulujeme - otevřeme prohlížeč, přejdeme na danou stránku, klikneme na tlačítko a voilà - úspěšně jsme vyřešili ASP.NET formuláře.

Počkat. Vyřešili jsme sice problém, ale jen teoreticky, takže jak to vlastně zprovozním? Velice jednoduše - pro `bakalarishell` stačí při startu přidat argumenty `-b PROHLÍŽEČ` a `-e CESTA_K_WEBDRIVERU` (pokud webdriver není na `PATH`), např. `-b Chrome -e webdriver.exe`; pro `bakalariapi` je potřeba při inicializaci třídy `BakalariAPI` přidat instanci `SeleniumHandler` (a zbytek snad odvodíš podle parametrů).
