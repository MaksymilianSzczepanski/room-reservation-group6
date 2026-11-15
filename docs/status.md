# Stan implementacji — 15 listopada 2026

## Dostępne w kodzie

- Osiem usług Django: users, rooms, guardians, reservations, decisions, notifications, search, reports.
- PostgreSQL z oddzielnymi schematami usług, Consul z trwałym katalogiem, Traefik i Docker Compose.
- Frontend React + PrimeReact w osobnym kontenerze Nginx; wykorzystuje logo i tło starszej wersji.
- Publiczna wyszukiwarka z filtrami i kalendarz miesiąc/tydzień/dzień (Europe/Warsaw).
- Logowanie pracownika, wniosek o rezerwację, lista własnych wniosków i anulowanie.
- Wyraźny wybór typu konta Pracownik w administracji; opcjonalne konto początkowe
  z `DJANGO_EMPLOYEE_*`, tworzone bez resetowania istniejących haseł.
- Powrót do wybranego terminu i formularza rezerwacji bezpośrednio po zalogowaniu.
- Panel opiekuna z przypisanymi salami, decyzjami i historią; komentarz wymagany przy odrzuceniu.
- Administracja salami, kontami, wyposażeniem i przypisaniami; raporty i historia powiadomień.
- Rezerwacje pending i approved blokują termin; brak automatycznego wygaszania.
- Trwałe zdarzenia i procesy ponawiające dostarczenie powiadomień oraz zastosowanie decyzji.

## Weryfikacja

- 18 testów Django we wszystkich ośmiu usługach przeszło.
- Test przez bramę `scripts/smoke_microservices.py` przeszedł, łącznie z anonimowym
  odczytem kalendarza i kontrolą, że nie zawiera danych prywatnych.
- Kompilacja frontendu w Dockerze przeszła.
- Po poprawkach kont pracowników przeszło 10 testów usług users i reservations.
- 7 testów Playwright przeszło w Chrome bez okna, z atrapami API: publiczny kalendarz,
  logowanie pracownika i wysyłanie wniosku, filtry wyposażenia, zaznaczanie godzin,
  ograniczenie dostępu do administracji, blokada składania wniosków przez studenta
  oraz anulowanie logowania.
- Na rzeczywistym koncie pracownika test przez API potwierdził logowanie, zapis wniosku,
  odczyt rezerwacji, anulowanie własnego wniosku i odmowę dostępu do administracji.
  Testowa rezerwacja została anulowana.

## Do zakończenia projektu

1. Dokończyć kontrolę interfejsu opiekuna i administratora, widoku telefonu
   oraz zachowania formularzy przy błędach API.
2. Przygotować końcowy raport zaliczeniowy i uzupełnić prezentację wynikami demonstracji.
3. Jeśli wymagane są rzeczywiste wiadomości e-mail: skonfigurować SMTP i sprawdzić dostarczenie.
   Obecnie domyślny backend poczty zapisuje wiadomości do logów.

## Ograniczenia i rozszerzenia

- Dane monolitu pozostają w public; nie ma automatycznej migracji do nowych schematów.
- Podpisany token zawiera rolę ważną przez godzinę; zmiana roli nie unieważnia go natychmiast.
- Serwer Django i brak TLS są przeznaczone do lokalnej demonstracji.
- CSV/PDF, edycja czasu istniejących rezerwacji i automatyczne wygaszanie wniosków
  nie są częścią tej implementacji. Zmianę rezerwacji realizuje anulowanie i nowy wniosek.
