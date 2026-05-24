# Room Reservation System

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

Repozytorium zawiera obecnie bazowy szkielet aplikacji Django z konfiguracja PostgreSQL i uruchamianiem w Dockerze. Kolejnymi krokami powinny byc:

- implementacja uwierzytelniania i autoryzacji
- przygotowanie modelu danych sal i rezerwacji
- rozbudowa panelu administratora
- integracja kalendarza rezerwacji

## Uruchomienie projektu

1. Upewnij sie, ze masz zainstalowane Docker i Docker Compose.
2. Uruchom projekt poleceniem:

```bash
docker compose up --build
```

3. Aplikacja bedzie dostepna pod adresem:

- `http://localhost:8000`

4. pgAdmin bedzie dostepny pod adresem:

- `http://localhost:8080`

## Testy

Testy znajduja sie glownie w pliku `room_reservations/tests.py` i sa uruchamiane przez wbudowany runner Django. W srodowisku lokalnym najwygodniej odpalac je z poziomu kontenera `web`.

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
docker compose exec web python manage.py test
```

Caly plik testow:

```bash
docker compose exec web python manage.py test room_reservations.tests
```

Jedna klasa testowa:

```bash
docker compose exec web python manage.py test room_reservations.tests.ReservationPermissionTests
```

Jeden test:

```bash
docker compose exec web python manage.py test room_reservations.tests.ReservationPermissionTests.test_new_reservation_sends_email_to_guardian
```

Bardziej szczegolowy output:

```bash
docker compose exec web python manage.py test room_reservations.tests --verbosity 2
```

Szybsza praca podczas poprawek:

```bash
docker compose exec web python manage.py test room_reservations.tests --keepdb --failfast
```

Podczas testow emaile nie sa wysylane na prawdziwy serwer SMTP. Testy korzystaja z backendu `locmem`, dzieki czemu mozna sprawdzac zawartosc `mail.outbox` bez wysylki realnych wiadomosci.

## Uwagi

- Migracje Django sa wykonywane automatycznie przy starcie kontenera `web`.
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
docker compose up --build
```

Jesli dane musza zostac zachowane, trzeba przywrocic poprzednie wartosci `DB_*` albo
zalogowac sie do istniejacej bazy i utworzyc brakujaca role lub baze recznie.
