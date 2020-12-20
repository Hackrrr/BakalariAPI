# **/HomeWorks/MarkAsFinished**
### Klíč: `homeworks_done`

# Metadata
| Název                             | Hodnota                    |
|-----------------------------------|:--------------------------:|
| Verze Bakalářů                    | 1.36.1214.1                |
| Datum verze Bakalářů              | 14. 12. 2020               |
| Datum poslední změny dokumentu    | 20. 12. 2020               |
| Potřeba Selenia?                  | Ne                         |

# Přehled
Pro normálního uživatele nedostupný endpoint. Stará se o změnu stavu "udělání" u úkolu.

# Request
```http
POST /HomeWorks/MarkAsFinished HTTP/1.1
homeworkId=*ID_ÚKOLU*&completed=*STAV*&studentId=*ID_STUDENTA*
```
Parametr `homeworkId`/`*ID_ÚKOLU*` je ID cíleného úkolu, paramter `completed`/`*STAV*` určuje, jaký stav se má nastavit (`true` je hotovo, `false` je nehotovo). Zvláštní je, že endpoint přijmá ID studenta (ID studenta je posíláno při normální interakci uživatele (viz "Výzkum")), avšak to vypadá, že se na něj nehledí.

# Response
Vrací se klasicky zabalená data:
```json
{"success":true,"error":"","data":null}
```
Zvláštností je, že požadavek bude **vždy** úspěšný podle vrácených dat, nehledě na neplatné ID studenta nebo úkolu.

# Výzkum
Ve verzi Bakalářů `1.35.1023.2` byla přidána možnost označit úkoly jako hotové a přes interaktivní checkbox byla nalezena JS funkce (kód funkce je ale vzat z verze `1.36.1207.1`):
```js
function markAsDone(homeworkId, studentId, checkbox) {
    var url = appRoot + "HomeWorks/MarkAsFinished";
    var completed = checkbox.is(":checked");
    var data = { homeworkId: homeworkId, completed: completed, studentId: studentId };
    Loading.Show();
    $.post(url, data)
        .done(function () {
            //nothing
        })
        .fail(function (jqXHR) {
            Utils.CatchError(jqXHR);
        })
        .always(function () {
            Loading.Hide();
        });
}
```