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
Pro normálního uživatele rychlý přehled. Pro nás nic zajímavého. Teoreticky by daly nějak exrahovat a využít data z panelů. `BakalariAPI` tuto stránku využívá k ověření správného přihlášení - Směřuje sem totiž redirect z úspěšného přihlášení (pokud se nespecifikuje jinak; viz endpoint `login`). Také sem přesměrovává i request/response na root (tzn. "/") pokud jsme přihlášeni.

# Request
```http
GET /dashboard HTTP/1.1
```
Nic speciálního.

# Výzkum
Nic speciálního. Co sem mám asi jako reálně napsat? LULW