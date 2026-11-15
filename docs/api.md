# Referencja API systemu rezerwacji sal

Adres bazowy lokalnej bramy: `http://localhost:8002/api/`.
Opis dotyczy implementacji z 15 listopada 2026 roku. Wszystkie ścieżki mają końcowy `/`.
Identyfikatory w przykładach należy zastąpić istniejącymi danymi.

## 1 Format i autoryzacja

Żądania z treścią używają `Content-Type: application/json`.
Listy są tablicami JSON bez paginacji. Błędy obsłużone przez `APIError` mają format:

```json
{"error": "Room is already reserved"}
```

| Oznaczenie w tabelach | Wymagany dostęp |
|---|---|
| Publiczny | Bez tokenu |
| Użytkownik | `Authorization: Bearer <token>` |
| Administrator | Token z `is_admin=true` |
| Opiekun | Token i przypisanie do sali sprawdzane w guardians |
| Właściciel lub administrator | Token oraz sprawdzenie autora rezerwacji albo is_admin |
| Wewnętrzny | `X-Service-Key: <SERVICE_KEY>` |

Token jest podpisanym tokenem Django, nie JWT. Wygasa po godzinie; nie ma endpointu
refresh ani serwerowego logout. `X-Service-Key` nie należy przekazywać do frontendu.
Ścieżki wewnętrzne są osiągalne przez te same reguły bramy i sprawdzają klucz w aplikacji.

Typowe kody odpowiedzi:

| Kod | Znaczenie |
|---|---|
| 200 | Odczyt, aktualizacja, anulowanie lub usunięcie zakończone |
| 201 | Utworzony rekord lub zastosowana nowa decyzja |
| 202 | Decyzja zapisana, zastosowanie oczekuje na ponowienie |
| 400 | Błąd walidacji obsłużony przez aplikację |
| 401 | Brak, niepoprawny lub wygasły token |
| 403 | Brak wymaganej roli, przypisania lub klucza wewnętrznego |
| 404 | Nie znaleziono zasobu |
| 405 | Niedozwolona metoda HTTP |
| 409 | Konflikt terminu, stanu lub unikatowości |
| 502 / 503 | Błąd zależności lub brak dostępnej usługi w discovery |

Nie wszystkie niepoprawne typy danych są przechwytywane; część może skutkować błędem
500. Nie należy traktować powyższej tabeli jako gwarancji pełnej walidacji każdego wejścia.

## 2 Konta i logowanie

| Metoda | Ścieżka | Dostęp | Działanie |
|---|---|---|---|
| POST | `/users/login/` | Publiczny | Wydanie tokenu i danych konta |
| GET | `/users/me/` | Użytkownik | Claims z tokenu |
| GET | `/users/` | Administrator | Wszystkie konta, również nieaktywne |
| POST | `/users/` | Administrator | Utworzenie konta |
| GET | `/users/{id}/` | Administrator | Dane konta |
| PATCH | `/users/{id}/` | Administrator | Zmiana danych, hasła lub uprawnień |
| DELETE | `/users/{id}/` | Administrator | Dezaktywacja, bez fizycznego usuwania |

Logowanie:

```json
{"username": "pracownik", "password": "HASLO_Z_LOKALNEGO_SRODOWISKA"}
```

Przykładowa odpowiedź:

```json
{
  "token": "PODPISANY_TOKEN",
  "user": {
    "id": 2,
    "username": "pracownik",
    "email": "pracownik@example.test",
    "is_admin": false,
    "is_student": false,
    "is_active": true
  }
}
```

Utworzenie pracownika wymaga `username` i `password`. Opcjonalne są `email`,
`is_admin` i `is_student`, przyjmujące przy tworzeniu wartości logiczne.
Domyślnie oba znaczniki roli są fałszywe. Nie ma pola zapisu `role=employee`.

```json
{
  "username": "pracownik2",
  "password": "WLASNE_HASLO",
  "email": "pracownik2@example.test",
  "is_admin": false,
  "is_student": false
}
```

Przy **PATCH** pole administratora nazywa się **`is_staff`**, nie `is_admin`.
Pozostałe obsługiwane pola: `email`, `first_name`, `last_name`, `is_active`, `password`,
`is_student`. Dane zwracane przez API obejmują pola widoczne w przykładzie `user`;
imiona i nazwiska nie są obecnie zwracane.
Zmiana hasła lub roli nie unieważnia już wydanego tokenu. Nieaktywne konto nie zaloguje się ponownie.

## 3 Sale i wyposażenie

| Metoda | Ścieżka | Dostęp | Działanie |
|---|---|---|---|
| GET | `/rooms/` | Publiczny | Lista i filtrowanie sal |
| POST | `/rooms/` | Administrator | Utworzenie sali |
| GET | `/rooms/{id}/` | Publiczny | Szczegóły sali |
| PATCH | `/rooms/{id}/` | Administrator | Aktualizacja sali |
| DELETE | `/rooms/{id}/` | Administrator | Usunięcie nieużywanej sali |
| GET | `/rooms/attributes/` | Publiczny | Lista wyposażenia |
| POST | `/rooms/attributes/` | Administrator | Dodanie atrybutu wyposażenia |

Filtry listy sal i wyszukiwarki:

| Parametr | Interpretacja |
|---|---|
| `building__icontains` | Fragment nazwy budynku, bez rozróżniania wielkości liter |
| `name__icontains` | Fragment nazwy sali |
| `capacity__gte` | Dolna granica liczby miejsc |
| `capacity__lte` | Górna granica liczby miejsc |
| `attributes__id` | ID wymaganego atrybutu; parametr można powtarzać |

Przykład: `/rooms/?capacity__gte=20&attributes__id=1&attributes__id=2`.
Wymagane jest jednoczesne posiadanie obu atrybutów.

Przykład utworzenia lub aktualizacji:

```json
{
  "name": "Sala 101",
  "building": "Budynek A",
  "capacity": 30,
  "description": "Sala wykładowa",
  "attribute_ids": [1, 2]
}
```

Nazwa jest wymagana i unikatowa. `attribute_ids` wskazuje istniejące atrybuty;
pusta tablica usuwa wyposażenie, pominięcie przy PATCH zachowuje poprzednie.
Odpowiedź zawiera `attributes: [{"id": 1, "name": "Komputer"}]`, a nie `attribute_ids`.
Backend dopuszcza pojemność 0; formularz administracyjny wymaga co najmniej 1.
Dodanie wyposażenia używa `{"name":"Komputer"}`. Brak endpointów jego edycji i usuwania.
Sala z dowolną historyczną rezerwacją lub opiekunem nie może zostać usunięta (`409`).

## 4 Przypisania opiekunów

| Metoda | Ścieżka | Dostęp | Działanie |
|---|---|---|---|
| GET | `/guardians/` | Administrator | Lista; opcjonalny filtr `room_id` |
| POST | `/guardians/` | Administrator | Utworzenie przypisania |
| DELETE | `/guardians/{id}/` | Administrator | Usunięcie przypisania |
| GET | `/guardians/mine/` | Użytkownik | Wyłącznie przypisania aktora z tokenu |

Treść POST: `{"user_id":2,"room_id":1}`. Odpowiedź dodaje ID przypisania.
Para jest unikatowa; powtórzenie daje `409`. Usługa sprawdza istnienie sali i aktywność konta.
Parametr `user_id` w `/mine/` nie zmienia właściciela zapytania.
Frontend proponuje aktywne konta bez flagi studenta; backend nie wprowadza takiego filtra roli
przy samym tworzeniu przypisania.

## 5 Rezerwacje i publiczny kalendarz

| Metoda | Ścieżka | Dostęp | Działanie |
|---|---|---|---|
| GET | `/reservations/calendar/` | Publiczny | Zajęte terminy wybranej sali |
| GET | `/reservations/` | Użytkownik | Lista; opcjonalny filtr `room_id` |
| POST | `/reservations/` | Użytkownik bez flagi studenta | Nowy wniosek |
| GET | `/reservations/{id}/` | Użytkownik | Odczyt rezerwacji |
| DELETE | `/reservations/{id}/` | Właściciel lub administrator | Zmiana statusu na cancelled |

Publiczny kalendarz wymaga dodatniego `room_id`. Opcjonalne `start` i `end` ograniczają
zakres i muszą występować razem, być świadome strefy czasu oraz spełniać `end > start`.
Zakres może obejmować wiele dni. Kalendarz zwraca wyłącznie `pending` i `approved`:

```json
[
  {
    "id": 10,
    "room_id": 1,
    "start": "2027-01-15T08:00:00+00:00",
    "end": "2027-01-15T09:00:00+00:00",
    "status": "pending"
  }
]
```

Przykład POST wniosku:

```json
{
  "room_id": 1,
  "title": "Konsultacje",
  "start": "2027-01-15T09:00:00+01:00",
  "end": "2027-01-15T10:00:00+01:00",
  "note": "Potrzebny rzutnik"
}
```

Daty są przykładowe; do testu wybierz wolny termin. Walidacja wymaga jednego dnia
w Warszawie, godzin 07:00–22:00 i końca późniejszego od początku. Brak wymogu przyszłej daty.
Konflikt z pending lub approved daje `409`. Konto jest dodatkowo odczytywane z users,
aby odrzucić tworzenie wniosku przez nieaktywną osobę.

Pełna odpowiedź zawiera `id`, `room_id`, `user_id`, `title`, `start`, `end`, `status`,
`note`, `decision_comment`. Przy utworzeniu dochodzi `notification_status`:
`sent` lub `pending_retry`. Sam wniosek jest zapisany w obu przypadkach.

GET chronione tokenem obecnie nie ogranicza wyników do właściciela. React filtruje
listę dla „Moich rezerwacji”. Nie należy opierać ochrony danych rzeczywistych wyłącznie
na tym filtrowaniu. DELETE zachowuje rekord i zwraca go ze statusem `cancelled`;
można anulować jedynie `pending` i `approved`. Nie ma PATCH rezerwacji.

## 6 Decyzje

| Metoda | Ścieżka | Dostęp | Działanie |
|---|---|---|---|
| GET | `/decisions/` | Użytkownik | Własne decyzje; administrator widzi wszystkie |
| POST | `/decisions/` | Opiekun danej sali | Zapisanie zatwierdzenia lub odrzucenia |

```json
{"reservation_id": 10, "status": "rejected", "comment": "Sala potrzebna na egzamin"}
```

Status to `approved` lub `rejected`. Przy odrzuceniu komentarz po usunięciu zewnętrznych
spacji nie może być pusty. Rezerwacja musi mieć `pending`, a aktor musi być opiekunem.
Samo `is_admin=true` nie omija sprawdzenia przypisania.

Przy powodzeniu: `201 {"id":1,"reservation":{...}}`.
Jeżeli decyzja jest zapisana, ale nie została zastosowana: `202 {"id":1,"status":"pending_retry"}`.
Konflikt stanu lub kolejna decyzja dla tego samego wniosku daje `409`.
Rekord listy zawiera też `guardian_id`, `comment`, `applied`, `blocked`, `last_error`, `created_at`.

## 7 Wyszukiwanie, raporty i historia powiadomień

| Metoda | Ścieżka | Dostęp | Działanie |
|---|---|---|---|
| GET | `/search/` | Publiczny | Filtry sal i opcjonalne wykluczenie zajętych |
| GET | `/reports/` | Administrator | Statystyki |
| GET | `/reports/occupancy/?start=RRRR-MM-DD&end=RRRR-MM-DD` | Opiekun lub administrator | Procent zajętości sal w okresie |
| GET | `/notifications/` | Administrator | Historia obsługi wiadomości |

`/search/` obsługuje filtry z rozdziału 3. Jeżeli podano **oba** `start` i `end`,
wyklucza sale z kolizją pending lub approved. Ten zakres podlega regule jednego dnia
07:00–22:00. Gdy podano tylko jedną granicę, aktualny kod nie stosuje filtra zajętości.
Spacje i znaki `+` w query należy kodować; do budowania zapytania używaj URLSearchParams lub urlencode.

Raport zwraca:

```json
{
  "room_count": 1,
  "reservation_count": 3,
  "status_counts": {"pending": 1, "approved": 1, "cancelled": 1},
  "approved_by_room": [{"room_id": 1, "room_name": "Sala 101", "count": 1}]
}
```

Licznik obejmuje także odrzucone i anulowane rekordy. W `status_counts` występują
tylko obecne statusy; nieobecny należy traktować jako 0.

### Raport zajętości sal

`GET /reports/occupancy/?start=2026-12-01&end=2026-12-31[&workdays=1][&room_id=1]`

Liczy, jaki procent czasu rezerwacji (07:00–22:00 czasu warszawskiego, 15 h dziennie)
zajmują rezerwacje w podanym okresie. Obie daty są włączone do okresu, który może mieć
najwyżej 366 dni. `workdays=1` pomija soboty i niedziele. `room_id` (można powtarzać)
zawęża raport do wybranych sal.

- **Opiekun** dostaje raport tylko dla przypisanych sal. Bez przypisań: `403`, a gdy
  poda `room_id` cudzej sali: `403`.
- **Administrator** dostaje raport dla wszystkich sal.
- Procent zajętości (`occupancy`) liczony jest **tylko z zatwierdzonych** rezerwacji.
  Oczekujące są podane osobno (`pending_hours`, `pending_share`), a odrzucone i anulowane są pomijane.

```json
{
  "start": "2026-12-01", "end": "2026-12-31", "workdays_only": true,
  "day_count": 23, "hours_per_day": 15,
  "total": {"room_count": 1, "available_hours": 345, "approved_hours": 69.0,
            "pending_hours": 3.0, "reservation_count": 12, "occupancy": 20.0, "pending_share": 0.9},
  "rooms": [{"room_id": 1, "name": "Sala 101", "building": "A", "capacity": 30,
             "available_hours": 345, "approved_hours": 69.0, "pending_hours": 3.0,
             "reservation_count": 12, "occupancy": 20.0, "pending_share": 0.9}],
  "by_weekday": [{"weekday": 0, "available_hours": 60, "approved_hours": 18.0, "occupancy": 30.0}]
}
```

`weekday` to 0 = poniedziałek … 6 = niedziela. W interfejsie raport jest w **Panel opiekuna →
Raport zajętości** oraz w **Administracja → Raporty**; przycisk „Pobierz CSV” zapisuje go
w formacie dla polskiego Excela (średnik, przecinek dziesiętny, UTF-8 z BOM).

Historia powiadomień zawiera `id`, `event_id`, `recipient`, `subject`, `state`, `error`,
`created_at`. Treść wiadomości `body` nie jest zwracana. `sent` przy konsolowym backendzie
oznacza zapisanie wiadomości do logów, nie dostarczenie do skrzynki.

## 8 Endpointy wewnętrzne

Wszystkie poniższe wymagają `X-Service-Key`. Służą komunikacji kontenerów, nie interfejsowi React.

| Metoda | Ścieżka | Odpowiedź lub cel |
|---|---|---|
| GET | `/users/internal/{id}/` | Dane konta bez hasła |
| GET | `/guardians/internal/check/?user_id=2&room_id=1` | `{"assigned":true}` |
| GET | `/guardians/internal/room/{room_id}/` | Przypisania sali |
| GET | `/guardians/internal/user/{user_id}/` | Sale przypisane opiekunowi |
| GET | `/reservations/internal/{id}/` | Pełna rezerwacja |
| POST | `/reservations/internal/{id}/decision/` | Zastosowanie `{status, comment}` |
| GET | `/reservations/internal/room/{room_id}/usage/` | `{"used":true}` dla dowolnej historii sali |
| GET | `/reservations/internal/occupied/?start=...&end=...` | Tablica ID sal z kolizją |
| GET | `/reservations/internal/all/[?start=...&end=...&room_id=1]` | Lista dla raportów; opcjonalnie tylko rezerwacje nachodzące na okres i wybrane sale |
| POST | `/notifications/internal/` | Obsługa `{kind, reservation}`; wynik `{"sent":liczba}` |

`kind` ma wartość `created` lub `decided`. Pole `reservation` zawiera dane zdarzenia
rezerwacji z identyfikatorami, terminem, tytułem i statusem. Zwykłe ponowienie nie wysyła
ponownie wiadomości zapisanej jako sent. Idempotencja ma ograniczenia awarii SMTP
opisane w [dokumentacji projektu](dokumentacja.md#7-cykl-rezerwacji-i-odporność).

Każdy kontener Django udostępnia także `GET /health/` z odpowiedzią
`{"service":"reservations","status":"ok"}`. To adres kontenera na porcie 8000,
nie publiczna ścieżka `http://localhost:8002/health/`, którą obsługuje frontend.

## 9 Przykład wywołania w PowerShell

```powershell
$baseUrl = 'http://localhost:8002/api'
$credential = Get-Credential -Message 'Konto pracownika'
$body = @{
    username = $credential.UserName
    password = $credential.GetNetworkCredential().Password
} | ConvertTo-Json
$session = Invoke-RestMethod -Method Post -Uri "$baseUrl/users/login/" `
    -ContentType 'application/json' -Body $body
$headers = @{ Authorization = "Bearer $($session.token)" }
Invoke-RestMethod -Uri "$baseUrl/users/me/" -Headers $headers
Invoke-RestMethod -Uri "$baseUrl/rooms/"
```

Przykład pobiera token do zmiennej i nie wymaga zapisywania hasła w dokumentacji.
Do kompletnego testu ośmiu usług służy [smoke_microservices.py](../scripts/smoke_microservices.py).
