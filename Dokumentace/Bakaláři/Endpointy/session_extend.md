# **/sessionextend**
### Klíč: `session_extend`

# Metadata
| Název                             | Hodnota                    |
|-----------------------------------|:--------------------------:|
| Verze Bakalářů                    | 1.36.1214.1                |
| Datum verze Bakalářů              | 14. 12. 2020               |
| Datum poslední změny dokumentu    | 20. 12. 2020               |
| Potřeba Selenia?                  | Ne                         |

# Přehled
Normálně nedostupný. Prodlužuje délku "životnosti" současné session na maximum. Funguje ale pouze v případě, že session je již za půlkou své životnosti.

*Pozn.: Je možné, že délka session je konfigurovatelná. To znamená, že je možné i to, že se session neprodlužuje na maximum ale na 900s (= 15 minut) a že životnost session musí být za/v 450s (= 7,5 minut), jelikož bylo zkoušeno pouze na jediném serveru, kde délka session je 900s (= 15 minut).*

# Request
Normálně (když se o to stará JS na klientské straně) se posílá GET request s parametrem `_`, který má hodnotu UNIX timestampy uživatele; tento parametr je ale opět k ničemu a opět (znovu a zase) endpoint funguje i bez toho.
```http
GET /sessionextend HTTP/1.1
```

# Response
Nevrací se nic. HTTP status kód je 200 (Ok).

# Výzkum
Endpoint nalezen odchytem při kliknutí na tlačítko "ANO, JSEM TU" (ještě bych něco dodal, ale nechci být neslušný :) ). Čas nutný pro obnovu (tedy polovina maximální životnosti session) byl zjištěn přes script, který neustále dotazoval endpointy [`session_info`](session_info.md) a `session_extend`. Tento script je integrován v shellu jako test 0 a tím pádem ho lze spustit v shellu přes příkaz `test 0`.
