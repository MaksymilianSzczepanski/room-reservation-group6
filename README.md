# System rezerwacji sal — mikroserwisy

Aktualna wersja uruchamia **osiem usług Django**: `users`, `rooms`, `guardians`,
`reservations`, `decisions`, `notifications`, `search` i `reports`. Osobny frontend
React + PrimeReact jest interfejsem, Traefik bramą API, Consul rejestrem usług, a PostgreSQL przechowuje dane
w osobnych schematach. Pełny opis przepływów i mapowanie na wymagania laboratorium
znajdują się w [docs/architecture.md](docs/architecture.md).

## Szybki start nowej architektury

1. Skopiuj `.env.example` do `.env` i ustaw własne hasła oraz trzy sekrety.
   Jeśli używasz istniejącego `.env`, dodaj `AUTH_SIGNING_KEY` i `SERVICE_KEY`.
2. Uruchom `docker compose up --build -d`.
3. Otwórz portal pod `http://localhost:8002/`. Panel Consul jest pod
   `http://localhost:8500/`.
4. Sale i kalendarz są dostępne bez logowania. Do administracji zaloguj się kontem
   `DJANGO_SUPERUSER_USERNAME` i `DJANGO_SUPERUSER_PASSWORD`.
5. Sprawdź wszystkie usługi poleceniem `python scripts/smoke_microservices.py`.

Każda usługa ma własne ścieżki `/api/<nazwa>/`. Przykładowo logowanie to
`POST /api/users/login/`, a lista sal to `GET /api/rooms/`. Test przejścia przez
bramę tworzy przykładowe dane, więc uruchamiaj go na lokalnej bazie demonstracyjnej.
Port 8002 pozwala jednocześnie zachować starą aplikację na porcie 8000.

Testy usług można uruchomić bez Dockera, np. w PowerShell:

```powershell
$env:SERVICE_NAME = 'reservations'
python microservices/manage.py test microservices.reservations
```

Gotowa prezentacja jest w [docs/prezentacja.html](docs/prezentacja.html),
a plan demonstracji w [docs/presentation.md](docs/presentation.md).
Stara aplikacja Django nadal może działać poleceniem
`docker compose --profile legacy up -d legacy-web` na porcie 8001. Jej dane
nie są automatycznie przenoszone do usług; stary frontend i jego testy
opisane poniżej dotyczą tej starszej wersji.

## Frontend React + PrimeReact

Kod interfejsu znajduje się w `frontend/`. Zachowuje tło, logo, wyszukiwarkę i układ
kalendarza starszej aplikacji. Nginx serwuje frontend w osobnym kontenerze,
a żądania `/api/` przechodzą przez Traefik do ośmiu usług Django.

- Student i gość: wyszukiwanie oraz publiczny kalendarz bez logowania.
- Pracownik: wnioski o rezerwację i anulowanie własnych rezerwacji.
- Opiekun: przypisane sale, oczekujące wnioski, decyzje i historia.
- Administrator: konta, sale, wyposażenie, przypisania, raporty i historia powiadomień.
  Zatwierdzanie wniosków wymaga również przypisania administratora jako opiekuna sali.

Wniosek oczekujący blokuje termin do decyzji lub anulowania i nie wygasa automatycznie.
Publiczny kalendarz udostępnia tylko identyfikator, salę, przedział czasu i status;
nie ujawnia tytułów, danych wnioskodawcy, uwag ani komentarzy decyzji.

Do pracy nad frontendem poza Dockerem potrzebny jest **Node.js 22.12 lub nowszy**:

```powershell
cd frontend
npm ci
npm run dev
```

Vite uruchamia interfejs na porcie 5173 i przekazuje API do `http://localhost:8002`.
Backend musi działać w Dockerze. `API_PROXY_TARGET` pozwala zmienić adres API.
Starszy portal techniczny Django jest opcjonalny (`legacy-portal`); domyślny interfejs
na porcie 8002 to React. Consul zachowuje rejestr usług w wolumenie `consul_data`.

Testy przeglądarkowe (wymagają działającego frontendu i Node.js 22.12+):

```powershell
cd frontend
npm ci
npx playwright install chromium
npm run test:e2e
```

Testy korzystają z atrap API i nie zmieniają bazy danych. Sprawdzają publiczny kalendarz,
złożenie wniosku oraz ograniczenie dostępu do administracji. Ich wykonanie pozostaje
do potwierdzenia na środowisku z dostępną przeglądarką.

Bieżący zakres i pozostałe zadania: [docs/status.md](docs/status.md).

## Archiwalny opis aplikacji jednoprocesowej

System rezerwacji sal zbudowany w Django z wykorzystaniem PostgreSQL. Docelowo aplikacja ma obslugiwac prezentacje kalendarza rezerwacji przy pomocy biblioteki FullCalendar.

## Cel projektu

Aplikacja ma umozliwiac zarzadzanie salami oraz ich rezerwowanie przez dwa typy kont:

- student
- pracownik
- administrator

Dodatkowo w systemie wystepuja role administracyjne i organizacyjne:

- admin - zarzadza calym systemem oraz dodaje konta uzytkownikow
- opiekun sali - zarzadza przypisana sala
- zwykly pracownik - moze przegladac sale i tworzyc rezerwacje

Nowi uzytkownicy nie rejestruja sie samodzielnie. Konta sa tworzone przez administratora w panelu administracyjnym.

## Glowny zakres funkcjonalny

- logowanie do systemu
- zarzadzanie uzytkownikami przez administratora
- zarzadzanie salami
- przypisywanie opiekuna do sali
- tworzenie, edycja i anulowanie rezerwacji
- przeglad kalendarza rezerwacji
- kontrola dostepu zalezna od typu konta i roli

## Stos technologiczny

- Django
- PostgreSQL
- Docker i Docker Compose
- FullCalendar jako planowana integracja dla widoku kalendarza

## Status projektu

Poniższy opis odnosi się do poprzedniej aplikacji Django. Jej modele i dane nie są źródłem danych nowych usług. Historycznie planowane były:

- implementacja uwierzytelniania i autoryzacji
- przygotowanie modelu danych sal i rezerwacji
- rozbudowa panelu administratora
- integracja kalendarza rezerwacji

## Uruchomienie projektu

1. Upewnij sie, ze masz zainstalowane Docker i Docker Compose.
2. Uruchom starszą aplikację poleceniem:

```bash
docker compose --profile legacy up --build -d legacy-web
```

3. Aplikacja bedzie dostepna pod adresem:

- `http://localhost:8001`

4. pgAdmin bedzie dostepny pod adresem:

- `http://localhost:8080` po `docker compose --profile tools up -d pgadmin`

## Testy

Testy starszej wersji znajdują się głównie w pliku `room_reservations/tests.py` i są uruchamiane przez wbudowany runner Django. W środowisku lokalnym można je uruchomić z kontenera `legacy-web`.

### Zakres testow

Obecny zestaw testow obejmuje przede wszystkim najwazniejsze reguly biznesowe aplikacji:

- uprawnienia do przegladania i tworzenia rezerwacji
- walidacje godzin rezerwacji i zakaz rezerwacji przechodzacej na kolejny dzien
- blokowanie nakladajacych sie rezerwacji
- wysylke emaili po utworzeniu rezerwacji oraz po akceptacji lub odrzuceniu wniosku
- filtrowanie sal po wielu atrybutach
- walidacje formularza admina przypisujacego opiekunow do sal
- bezpieczne przekierowania i obsluge bledow logowania
- licznik oczekujacych rezerwacji dla opiekuna sali
- API wydarzen wyswietlanych w kalendarzu

Najwazniejsze klasy testowe:

- `ReservationPermissionTests` - rezerwacje, uprawnienia i emaile
- `RoomSearchAttributeFilterTests` - filtrowanie sal po atrybutach
- `RoomGuardianAdminFormTests` - walidacja formularza admina
- `ReservationHoursHelperTests` - helper sprawdzajacy dozwolone godziny
- `ReservationModelValidationTests` - konflikty i statusy rezerwacji
- `ReservationPermissionHelperTests` - helper uprawnien
- `SearchAndLoginFlowTests` - logowanie i bezpieczne `next`
- `GuardianPendingCountTests` - licznik oczekujacych prosb
- `CalendarEventsViewTests` - feed danych do kalendarza

### Uruchamianie testow

Wszystkie testy:

```bash
docker compose exec legacy-web python manage.py test
```

Caly plik testow:

```bash
docker compose exec legacy-web python manage.py test room_reservations.tests
```

Jedna klasa testowa:

```bash
docker compose exec legacy-web python manage.py test room_reservations.tests.ReservationPermissionTests
```

Jeden test:

```bash
docker compose exec legacy-web python manage.py test room_reservations.tests.ReservationPermissionTests.test_new_reservation_sends_email_to_guardian
```

Bardziej szczegolowy output:

```bash
docker compose exec legacy-web python manage.py test room_reservations.tests --verbosity 2
```

Szybsza praca podczas poprawek:

```bash
docker compose exec legacy-web python manage.py test room_reservations.tests --keepdb --failfast
```

Podczas testow emaile nie sa wysylane na prawdziwy serwer SMTP. Testy korzystaja z backendu `locmem`, dzieki czemu mozna sprawdzac zawartosc `mail.outbox` bez wysylki realnych wiadomosci.

## Uwagi

- Migracje starszej aplikacji Django są wykonywane przy starcie kontenera `legacy-web`.
- Konfiguracja srodowiska lokalnego znajduje sie w pliku `.env`.

## Rozwiazywanie problemow

Jesli po starcie widzisz komunikaty podobne do:

- `FATAL: role "postgres" does not exist`
- `password authentication failed for user "postgres"`

to najczesciej oznacza, ze wolumen `postgres_data` zostal utworzony wczesniej z innymi
wartosciami `DB_NAME`, `DB_USER` lub `DB_PASS` niz te, ktore sa teraz w `.env`.

W kontenerze `postgres` zmienne `POSTGRES_*` sa brane pod uwage tylko przy pierwszej
inicjalizacji katalogu danych.

Jesli to lokalna baza testowa i mozna ja odtworzyc od zera:

```bash
docker compose down -v
docker compose --profile legacy up --build -d legacy-web
```

Jesli dane musza zostac zachowane, trzeba przywrocic poprzednie wartosci `DB_*` albo
zalogowac sie do istniejacej bazy i utworzyc brakujaca role lub baze recznie.
