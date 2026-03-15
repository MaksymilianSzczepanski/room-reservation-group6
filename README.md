# Room Reservation System

System rezerwacji sal zbudowany w Django z wykorzystaniem PostgreSQL. Docelowo aplikacja ma obslugiwac prezentacje kalendarza rezerwacji przy pomocy biblioteki FullCalendar.

## Cel projektu

Aplikacja ma umozliwiac zarzadzanie salami oraz ich rezerwowanie przez dwa typy kont:

- student
- pracownik

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

## Uwagi

- Migracje Django sa wykonywane automatycznie przy starcie kontenera `web`.
- Konfiguracja srodowiska lokalnego znajduje sie w pliku `.env`.
