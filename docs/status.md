# Stan implementacji — 14 listopada 2026

## Dostępne w kodzie

- Osiem usług Django: users, rooms, guardians, reservations, decisions, notifications, search, reports.
- PostgreSQL z oddzielnymi schematami usług, Consul z trwałym katalogiem, Traefik i Docker Compose.
- Frontend React + PrimeReact w osobnym kontenerze Nginx; wykorzystuje logo i tło starszej wersji.
- Publiczna wyszukiwarka z filtrami i kalendarz miesiąc/tydzień/dzień (Europe/Warsaw).
- Logowanie pracownika, wniosek o rezerwację, lista własnych wniosków i anulowanie.
- Panel opiekuna z przypisanymi salami, decyzjami i historią; komentarz wymagany przy odrzuceniu.
- Administracja salami, kontami, wyposażeniem i przypisaniami; raporty i historia powiadomień.
- Rezerwacje pending i approved blokują termin; brak automatycznego wygaszania.
- Trwałe zdarzenia i procesy ponawiające dostarczenie powiadomień oraz zastosowanie decyzji.

## Weryfikacja

- 18 testów Django we wszystkich ośmiu usługach przeszło.
- Test przez bramę `scripts/smoke_microservices.py` przeszedł, łącznie z anonimowym
  odczytem kalendarza i kontrolą, że nie zawiera danych prywatnych.
- Kompilacja frontendu w Dockerze przeszła.
- Sprawdzenie wyglądu i formularzy w przeglądarce nie zostało zakończone: narzędzie
  dostępu do przeglądarki było niedostępne, a próba użycia okna Windows została zatrzymana
  przez narzędzie, ponieważ nie potrafiło wiarygodnie ustalić bieżącego adresu strony.

## Do zakończenia projektu

1. Przejść scenariusze w interfejsie jako gość, pracownik, opiekun i administrator;
   sprawdzić widok telefonu i zachowanie formularzy przy błędach API.
2. Przygotować końcowy raport zaliczeniowy i uzupełnić prezentację wynikami demonstracji.
3. Jeśli wymagane są rzeczywiste wiadomości e-mail: skonfigurować SMTP i sprawdzić dostarczenie.
   Obecnie domyślny backend poczty zapisuje wiadomości do logów.

## Ograniczenia i rozszerzenia

- Dane monolitu pozostają w public; nie ma automatycznej migracji do nowych schematów.
- Podpisany token zawiera rolę ważną przez godzinę; zmiana roli nie unieważnia go natychmiast.
- Serwer Django i brak TLS są przeznaczone do lokalnej demonstracji.
- CSV/PDF, edycja czasu istniejących rezerwacji i automatyczne wygaszanie wniosków
  nie są częścią tej implementacji. Zmianę rezerwacji realizuje anulowanie i nowy wniosek.
