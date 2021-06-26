# /dashboard
### Klíč: `dashboard`

# Metadata
| Název                             | Hodnota                    |
|-----------------------------------|:--------------------------:|
| Verze Bakalářů                    | 1.36.1214.1                |
| Datum verze Bakalářů              | 14. 12. 2020               |
| Datum poslední změny dokumentu    | 20. 12. 2020               |
| Potřeba Selenia?                  | Ne                         |

# Přehled
Pro normálního uživatele rychlý přehled, pro nás nic zajímavého. Teoreticky by se dala nějak extrahovat a využít data z panelů. Směřuje sem totiž přesměrování z úspěšného přihlášení (pokud se nespecifikuje jinak; viz [endpoint `login`](login.md)). Také sem přesměrovává i request/response na root (tzn. "/") pokud jsme přihlášeni.

# Request
```http
GET /dashboard HTTP/1.1
```
Nic speciálního.

# Výzkum
Nic speciálního. Co sem mám asi jako reálně napsat? LULW