# **/logout**
### Klíč: `logout`

# Metadata
| Název                             | Hodnota                    |
|-----------------------------------|:--------------------------:|
| Verze Bakalářů                    | 1.36.1214.1                |
| Datum verze Bakalářů              | 14. 12. 2020               |
| Datum poslední změny dokumentu    | 20. 12. 2020               |
| Potřeba Selenia?                  | Ne                         |

# Přehled
Odhlásí uživatele. Toť vše. Neposíláme žádný parametry, jen requestneme stránku. Actually je tohle login stránka (která login ověřuje přes reálnou login stránku), která vás ale předtím odhlásí a od skutečný login stránky se liší pouze v "detailech". Může vzniknout "vtipná" situace, když chcete navštívit tuto stránku, když nsjte nepřihlášeni - To má za následek to, že vás to přesměruje na reálnou login stránku (protože nejste přihlášení a tuto stránku můžete nsjšpíše navšívit jen jako přihlášený uživatel) s parametrem `returnUrl` jehož hodnota je `logout`, takže pokud se na reálně login stránce nyní přihlásíte, tak budete automaticky hned odlášeni LULW . BTW když už jsme u `returnUrl` parametru, tak ten tato stránka v GET requestu nepodporuje.

# Request
Posílá se GET request:
```http
GET /logout HTTP/1.1
```

# Response
Vrátí se HTML. Stejně vypadající jako reálná login stránka až na to, že má navíc text ve smyslu něco jako "byly jste odhlášeni".

# Výzkum
Link na tento enpoint se získal přes normální odhlášení.