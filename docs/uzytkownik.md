# Instrukcja użytkownika systemu rezerwacji sal

Aplikację lokalną otworzysz pod [http://localhost:8002/](http://localhost:8002/).
Jeżeli strona jest niedostępna, osoba administrująca uruchamia środowisko według
[instrukcji utrzymania](utrzymanie.md).

## 1 Student lub gość

Student nie musi się logować. Może wyszukiwać sale, czytać ich opisy i wyposażenie
oraz sprawdzać kalendarz. Publiczne wydarzenia pokazują status zajętości, bez autora
i treści wniosku. Gość nie może wysłać ani anulować rezerwacji.

1. Na stronie głównej wybierz budynek lub wpisz fragment nazwy sali.
2. Opcjonalnie ustaw minimalną i maksymalną liczbę miejsc.
3. Zaznacz wymagane wyposażenie. Wynik musi zawierać wszystkie wybrane elementy.
4. Zatwierdź filtry przyciskiem **Szukaj**; wybór podpowiedzi lub wyposażenia aktualizuje wyniki.
5. Przy wybranej sali kliknij **Kalendarz**.
6. Przełącz widok miesiąca, tygodnia lub dnia i sprawdź zajęte godziny.

**Reset** usuwa wszystkie filtry. Wyczyść wyposażenie usuwa tylko wybrane atrybuty.
Lista wyników jest katalogiem sal zgodnych z filtrami, nie potwierdzeniem dostępności
na konkretną godzinę. Dostępność sprawdź w kalendarzu.

## 2 Logowanie pracownika

Administrator zakłada konto i przekazuje login oraz hasło. Nie ma samodzielnej rejestracji.
Kliknij **Zaloguj** w górnym pasku i podaj swoje dane. Ten sam formularz obsługuje
pracowników, opiekunów i administratorów; uprawnienia wynikają z konta.
Po zalogowaniu widoczny jest login i typ konta.

Nie ma wspólnego, stałego hasła dla wszystkich instalacji. Początkowe dane administratora
pochodzą z lokalnego `DJANGO_SUPERUSER_*`, a opcjonalnego pracownika z `DJANGO_EMPLOYEE_*`.
Hasła kont utworzonych w interfejsie ustawia administrator.

Token jest ważny godzinę. Po wygaśnięciu zaloguj się ponownie. Przycisk **Wyloguj**
usuwa sesję z bieżącej karty. W sprawie zapomnianego hasła skontaktuj się z administratorem.

## 3 Składanie wniosku

1. Otwórz kalendarz sali.
2. Kliknij **Zarezerwuj salę**, dzień w widoku miesiąca albo zaznacz godziny w tygodniu lub dniu.
3. Jeżeli nie jesteś zalogowany, aplikacja poprosi o login. Po zalogowaniu wróci do wybranego terminu.
4. Wpisz tytuł, początek, koniec i opcjonalne uwagi dla opiekuna.
5. Sprawdź daty w strefie czasu Warszawy i kliknij **Wyślij wniosek**.

Rezerwacja musi mieścić się w jednym dniu, w godzinach **07:00–22:00**.
Koniec musi być późniejszy od początku. Termin nie może kolidować z inną rezerwacją
oczekującą ani zatwierdzoną. Ostateczną kontrolę wykonuje serwer przy zapisie,
więc równoległy wniosek innej osoby może spowodować odrzucenie wybranego terminu.

Pomyślny zapis daje status **Oczekuje**. To jeszcze nie jest zgoda opiekuna.
Od chwili zapisu wniosek blokuje termin aż do decyzji albo anulowania i nie wygasa sam.
Komunikat o ponowieniu powiadomienia oznacza, że wniosek już istnieje; nie wysyłaj go drugi raz.

## 4 Moje rezerwacje i anulowanie

Wejdź w **Moje rezerwacje**. Zobaczysz swoje oczekujące wnioski i pozostałe rekordy
z datami, salą, statusem i komentarzem decyzji, jeśli występuje.

| Status | Znaczenie | Czy blokuje termin |
|---|---|---|
| Oczekuje | Wniosek czeka na opiekuna | Tak |
| Zatwierdzona | Opiekun zaakceptował wniosek | Tak |
| Odrzucona | Opiekun odmówił i podał komentarz | Nie |
| Anulowana | Właściciel lub administrator anulował rezerwację | Nie |

Aby wycofać własny wniosek lub zatwierdzoną rezerwację, kliknij **Anuluj** i potwierdź.
Rekord pozostaje w historii. Nie można anulować rekordu już odrzuconego ani anulowanego.
Do zmiany sali, tytułu lub terminu anuluj poprzedni wniosek i utwórz nowy.

## 5 Panel opiekuna

Panel pojawia się po przypisaniu co najmniej jednej sali przez administratora.
Pracownik może jednocześnie składać własne wnioski i być opiekunem sal.

1. Zaloguj się i wejdź w **Panel opiekuna**.
2. Sprawdź **Twoje sale**, **Zgłoszenia** lub **Podsumowanie**.
3. W oczekującym wniosku wybierz **Rozpatrz wniosek**.
4. Kliknij **Zatwierdź** albo wpisz uzasadnienie i kliknij **Odrzuć**.
5. W **Historii** sprawdź wynik operacji.

Odrzucenie wymaga komentarza. Decyzję może wydać tylko opiekun konkretnej sali.
Administrator bez tego przypisania również nie może zatwierdzać wniosku.
Jeśli decyzja oczekuje na przekazanie do rezerwacji, jest już zapisana i zostanie
ponowiona przez proces pomocniczy. Przy komunikacie o konflikcie skontaktuj się z administratorem.

## 6 Administracja

Po zalogowaniu kontem administratora otwórz **Administracja**.

| Zakładka | Czynności |
|---|---|
| Sale | Dodanie, edycja i usunięcie nieużywanej sali; wybór wyposażenia |
| Użytkownicy | Założenie konta, typ Pracownik lub Administrator lub Student, hasło i aktywność |
| Opiekunowie | Przypisanie aktywnego pracownika lub administratora do sali i usunięcie przypisania |
| Wyposażenie | Dodanie nazwy wyposażenia |
| Raporty | Liczba sal, rezerwacji i zatwierdzonych wniosków według sal |
| Powiadomienia | Historia obsługi wiadomości i błędy wysyłki |

Do uruchomienia pełnego scenariusza utwórz salę, konto pracownika, konto opiekuna lub
wykorzystaj istniejące, a następnie przypisz opiekuna do sali. Uzupełnij adresy e-mail,
jeżeli mają być wykorzystywane powiadomienia. Opiekunem może być także administrator.

**Usunięcie użytkownika dezaktywuje konto.** Historia rezerwacji pozostaje w bazie.
Usunięcie sali jest blokowane także przez historyczne rezerwacje i przypisania.
Pozostawienie pola nowego hasła pustego podczas edycji zachowuje poprzednie hasło.
Zmiana roli nie unieważnia od razu już wydanego tokenu.

Raporty są zestawieniami w interfejsie i JSON w API. Eksport CSV/PDF nie jest dostępny.
Panel administracyjny zarządza danymi aplikacji; start, stop i restart kontenerów
wykonuje się przez Docker Desktop albo [polecenia administracyjne](utrzymanie.md#4-zarządzanie-kontenerami).

## 7 Najczęstsze komunikaty

| Sytuacja | Działanie użytkownika |
|---|---|
| Nieprawidłowy login lub hasło | Sprawdź dane i Caps Lock; administrator może ustawić nowe hasło |
| Sesja wygasła | Zaloguj się ponownie |
| Termin zajęty | Wybierz inną godzinę lub salę i odśwież kalendarz |
| Rezerwacja poza godzinami | Ustaw jeden dzień, 07:00–22:00, według czasu Warszawy |
| Brak uprawnień opiekuna | Administrator sprawdza przypisanie do tej sali |
| Usługa chwilowo niedostępna | Nie powtarzaj wielokrotnie zapisu; sprawdź listę i zgłoś problem administratorowi |
| Wniosek zapisany, powiadomienie będzie ponowione | Wniosek już blokuje termin; oczekuj na decyzję |

W lokalnej konfiguracji poczta trafia do logów kontenera. Jej obecność w historii
nie oznacza dostarczenia do skrzynki, dopóki administrator nie skonfiguruje SMTP.
