# Uruchomienie i utrzymanie systemu rezerwacji sal

Polecenia Docker Compose wykonuj w katalogu z [docker-compose.yml](../docker-compose.yml).
Przykłady dla Windows używają PowerShell. Dokument opisuje lokalną instalację projektu,
nie wdrożenie produkcyjne.

## 1 Wymagania i konfiguracja

Do uruchomienia wystarczy działający Docker z Docker Compose i kontenerami Linux.
Python 3.11 jest potrzebny lokalnie do testów backendu i skryptu smoke. Node.js 22.12
lub nowszy jest potrzebny tylko do pracy nad frontendem poza Dockerem.

```powershell
cd C:\sudia_2026\system_rezerwacji
docker version
docker compose version
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

W Bash, WSL lub Linux, po wejściu do katalogu repozytorium:

```bash
test -f .env || cp .env.example .env
```

Uzupełnij `.env` własnymi wartościami. Nie nadpisuj istniejącego pliku z działającą
konfiguracją. Szablon nie zawiera gotowych haseł do rzeczywistej instalacji.

| Zmienne | Przeznaczenie |
|---|---|
| `SECRET_KEY` | Klucz Django |
| `AUTH_SIGNING_KEY` | Wspólny klucz podpisu tokenów użytkowników |
| `SERVICE_KEY` | Wspólny klucz wewnętrznej komunikacji usług |
| `DB_NAME`, `DB_USER`, `DB_PASS` | Baza, konto i hasło PostgreSQL |
| `DB_HOST`, `DB_PORT` | Adres bazy; Compose wymusza DB_HOST=db dla usług Django |
| `DJANGO_SUPERUSER_USERNAME`, `DJANGO_SUPERUSER_PASSWORD`, `DJANGO_SUPERUSER_EMAIL` | Początkowe konto administratora |
| `DJANGO_EMPLOYEE_USERNAME`, `DJANGO_EMPLOYEE_PASSWORD`, `DJANGO_EMPLOYEE_EMAIL` | Opcjonalne początkowe konto pracownika |
| `DEBUG`, `ALLOWED_HOSTS` | Ustawienia Django; ALLOWED_HOSTS nie ma w szablonie, można je dodać |
| `PGADMIN_EMAIL`, `PGADMIN_PASSWORD` | Dane opcjonalnego pgAdmin |
| `EMAIL_BACKEND`, `DEFAULT_FROM_EMAIL`, `EMAIL_*` | Obsługa poczty |

Trzy klucze ustaw jako różne losowe wartości. Przykład wygenerowania jednego:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

`AUTH_SIGNING_KEY` i `SERVICE_KEY` muszą być spójne między usługami. Nie kopiuj ich
do kodu React. `.env` jest ignorowany przez Git i wykluczony z obrazu przez `.dockerignore`.

Początkowy administrator i pracownik tworzą się tylko, gdy konto o danym loginie
nie istnieje. Zmiana hasła w `.env` nie resetuje hasła już istniejącego konta.
Dla pracownika obie zmienne loginu i hasła muszą być uzupełnione albo obie puste.
Kolizja loginu pracownika z nieaktywnym kontem lub inną rolą zatrzyma start `users`.

## 2 Pierwsze uruchomienie

```bash
docker compose build users frontend
docker compose up -d
docker compose ps -a
```

Najpierw budowany jest wspólny obraz Django oraz obraz React/Nginx. Po starcie bazy
usługi tworzą własne schematy, wykonują migracje, zakładają konta początkowe w users,
rejestrują się w Consul i uruchamiają serwery. Rejestracja i kontrole zdrowia wymagają chwili.

| Adres | Zastosowanie |
|---|---|
| `http://localhost:8002/` | Frontend React i brama API |
| `http://localhost:8500/` | Panel Consula |
| `http://localhost:5173/` | Vite tylko podczas lokalnego developmentu |
| `http://localhost:8001/` | Starszy monolit po włączeniu profilu legacy |
| `http://localhost:8080/` | pgAdmin po włączeniu profilu tools |

Nowe usługi Django nie mają osobnych portów wystawionych na hosta.
PostgreSQL działa w sieci Compose na `db:5432`. Frontend jest dostępny przez Traefik.
Port 8000 może należeć do pozostałości wcześniejszej instalacji; nowy Compose używa
dla opcjonalnego monolitu portu 8001.

Po zalogowaniu jako administrator utwórz salę, pracownika i przypisanie opiekuna.
W pustej instalacji nie ma gotowych sal. Migracja rooms dodaje początkowe atrybuty wyposażenia.
Pełny scenariusz użytkownika: [uzytkownik.md](uzytkownik.md).

## 3 Sprawdzanie działania

```bash
docker compose ps -a
docker compose logs --tail=80 users rooms reservations
docker compose logs --tail=50 -f reservations
```

`running` oznacza działający proces kontenera, `healthy` poprawną kontrolę Docker.
Wyjście z podglądu logów przez `Ctrl+C` nie zatrzymuje usługi.
W Consul wybierz **Services**, następnie nazwę i kontrole zdrowia.
`passing` oznacza poprawny wynik sprawdzenia, `critical` błąd lub maintenance.

Sprawdzenie pojedynczego HTTP health check bezpośrednio w kontenerze:

```bash
docker compose exec reservations python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/health/').read().decode())"
```

`/health/` sprawdza odpowiedź procesu HTTP, nie dostępność bazy i wszystkich zależności.
Do kontroli funkcjonalnej używaj także API i skryptu smoke opisanego w rozdziale 9.

## 4 Zarządzanie kontenerami

| Czynność | Polecenie |
|---|---|
| Start całej aplikacji w tle | `docker compose up -d` |
| Zatrzymanie całej aplikacji | `docker compose stop` |
| Uruchomienie usługi z zależnościami | `docker compose up -d reservations` |
| Zatrzymanie usługi | `docker compose stop reservations` |
| Restart usługi | `docker compose restart reservations` |
| Podgląd procesów ponawiających | `docker compose logs --tail=80 reservation-worker decision-worker` |

Do wyboru są `users`, `rooms`, `guardians`, `reservations`, `decisions`, `notifications`,
`search`, `reports`, `frontend`, `gateway`, `consul`, `db` i dwa procesy pomocnicze.
Docker Desktop udostępnia podobne operacje w **Containers → system_rezerwacji**.
Consul pokazuje stan rejestru; nie steruje procesami kontenerów.

Wszystkie usługi backendu korzystają z jednego obrazu, którego budowanie deklaruje `users`.
Po zmianach kodu backendu:

```bash
docker compose build users
docker compose up -d
```

Po zmianach frontendu:

```bash
docker compose build frontend
docker compose up -d frontend
```

Zmiana `.env` wymaga odtworzenia kontenerów przez `up -d`; samo `restart` nie wczyta
nowych zmiennych. Ponieważ `.env` jest używane również przez db, zmiana pliku może
spowodować odtworzenie kontenera bazy z zachowaniem wolumenu i chwilową przerwę połączeń.
Docker Compose odtwarza kontenery po zmianie konfiguracji lub obrazu, zachowując zamontowane
wolumeny. [Dokumentacja Docker Compose up](https://docs.docker.com/reference/cli/docker/compose/up/)

## 5 Tryb maintenance w Consul

Maintenance oznacza wyłączenie usługi z wyboru zdrowych instancji. Jej kontener nadal
działa. To mechanizm Consula, odrębny od Docker stop.
[Dokumentacja Consul maint](https://developer.hashicorp.com/consul/commands/maint)

Włączenie dla rezerwacji:

```bash
docker compose exec consul consul maint -enable -service=reservations -reason="Prace serwisowe"
```

Lista aktywnych maintenance:

```bash
docker compose exec consul consul maint
```

Wyłączenie i przywrócenie udziału w discovery:

```bash
docker compose exec consul consul maint -disable -service=reservations
```

`-service` wskazuje ID rejestracji, w tej aplikacji równe nazwie usługi. Sprawdź
kontrolę maintenance w panelu Consula. Wywołania `common.py` wybierają tylko instancje
passing, więc usługa w maintenance nie będzie wybrana. Zależne funkcje mogą być niedostępne.
Po zakończeniu demonstracji lub prac wyłącz maintenance jawnie.

## 6 Poczta i konfiguracja SMTP

Domyślnie `EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend`.
Wiadomości są widoczne w `docker compose logs notifications`.
Do rzeczywistej wysyłki ustaw w lokalnym `.env` wartości własnego serwera:

```dotenv
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.example.invalid
EMAIL_PORT=587
EMAIL_HOST_USER=TWOJ_LOGIN
EMAIL_HOST_PASSWORD=TWOJE_HASLO
EMAIL_USE_TLS=1
EMAIL_TIMEOUT=5
DEFAULT_FROM_EMAIL=rezerwacje@example.invalid
```

To przykład, nie działająca konfiguracja. Mikroserwisy włączają TLS wyłącznie dla wartości
`1`; nie używaj tutaj `True`. Następnie wykonaj `docker compose up -d notifications`.
Uzupełnij adresy e-mail opiekunów i pracowników. Brak adresu lub opiekuna oznacza pominięcie odbiorcy.

Zdarzenia `created` trafiają do opiekunów, a `decided` do wnioskodawcy.
Anulowanie nie tworzy obecnie osobnego zdarzenia e-mail. Stan sent z backendu konsolowego
nie zostanie automatycznie wysłany ponownie po późniejszej konfiguracji SMTP.

## 7 Trwałość i kopia bazy

Wolumen `postgres_data` przechowuje wszystkie schematy usług i ewentualne dane monolitu.
`consul_data` przechowuje katalog Consula. Zwykłe zatrzymanie i odtworzenie kontenerów
nie usuwa tych danych. Opcje usuwania wolumenów nie są procedurą codziennego restartu.

Przykład kopii PostgreSQL w PowerShell. Plik binarny powstaje wewnątrz kontenera,
a potem jest kopiowany, co unika problemów kodowania binarnego przez starszy PowerShell:

```powershell
New-Item -ItemType Directory -Force backups | Out-Null
docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc -f /tmp/rezerwacje.dump'
docker compose cp db:/tmp/rezerwacje.dump backups/rezerwacje.dump
```

Kopia zawiera dane aplikacji i hashe haseł. Przechowuj ją poza publicznym repozytorium.
Polecenie nadpisze poprzedni plik o tej nazwie; do kolejnych kopii stosuj własne datowane nazwy.
Odtwarzanie sprawdzaj na osobnej bazie testowej przed użyciem na działającej instalacji.
Plik `backup_bazy.sql` w katalogu głównym jest materiałem starszej aplikacji,
a nie potwierdzoną bieżącą kopią wszystkich schematów mikroserwisów.

## 8 Praca programistyczna

Backend w Dockerze używa Python 3.11. W testach lokalnych przygotuj środowisko
z zależnościami z requirements.txt, np. na Windows:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:SERVICE_NAME = 'users'
.venv\Scripts\python.exe microservices/manage.py test microservices.users
```

Testy domyślnie korzystają z SQLite w pamięci. Pełny start usługi poza Dockerem
wymaga też PostgreSQL, właściwego schematu, Consula i zgodnych adresów; samo
`MICROSERVICES_SQLITE=1` nie tworzy kompletnej infrastruktury.

Frontend, przy działającym backendzie na porcie 8002:

```powershell
cd frontend
npm ci
npm run dev
```

Vite używa portu 5173 i proxy `/api/` do `http://localhost:8002`.
`API_PROXY_TARGET` zmienia cel proxy developmentu. Nie jest adresem wpisywanym
do produkcyjnego klienta React. Do kompilacji służy `npm run build`.

## 9 Testy i scenariusz odbioru

Wszystkie testy backendu w PowerShell, z aktywnym środowiskiem Pythona:

```powershell
$serviceNames = 'users','rooms','guardians','reservations','decisions','notifications','search','reports'
foreach ($serviceName in $serviceNames) {
    $env:SERVICE_NAME = $serviceName
    python microservices/manage.py test "microservices.$serviceName"
    if ($LASTEXITCODE -ne 0) { throw "Błąd testów usługi $serviceName" }
}
```

Test przejścia przez rzeczywistą bramę, Consul, bazę i osiem usług:

```powershell
python scripts/smoke_microservices.py
```

Skrypt odczytuje dane administratora ze środowiska lub `.env` i domyślnie używa portu
8002. `API_URL` zmienia ten adres. Tworzy pracownika, salę, przypisanie, rezerwację,
decyzję i powiadomienia; **pozostawia dane testowe w bazie**. Wykonuj go na lokalnej
bazie demonstracyjnej. Wynik `{"result":"ok", ...}` potwierdza przejście scenariusza,
nie test obciążenia ani dostarczenie wiadomości do skrzynki.

Testy przeglądarkowe z atrapami API, przy działającym frontendzie:

```powershell
cd frontend
npm ci
npx playwright install chromium
npm run test:e2e
```

`FRONTEND_URL` zmienia adres strony w testach. Opcjonalnie ustaw
`PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH` na istniejący Chrome. Testy nie zapisują danych w bazie.
Wyniki i zakres ostatniej weryfikacji: [dokumentacja projektu](dokumentacja.md#9-testy-i-potwierdzone-wyniki).

Odbiór ręczny powinien obejmować wyszukanie sali jako gość, brak danych prywatnych
w kalendarzu, logowanie pracownika, wniosek i konflikt drugiego terminu, decyzję opiekuna
z komentarzem odrzucenia, anulowanie, raport i historię powiadomień. Osobno sprawdź
brak administracji u pracownika, maintenance oraz ponawianie po przerwie notifications.
Na końcu przywróć zatrzymane usługi i wyłącz maintenance.

## 10 Typowe problemy

| Objaw | Sprawdzenie lub rozwiązanie |
|---|---|
| Strona 8002 nie działa | `docker compose ps -a`, logi gateway i frontend; sprawdź zajętość portu |
| API ma błąd zależności | Sprawdź Consul, zdrowie i maintenance usługi oraz jej logi |
| Usługa jest running, ale funkcja nie działa | Health sprawdza tylko HTTP; sprawdź bazę, zależności i logi workerów |
| Zmiany kodu niewidoczne | Zbuduj właściwy obraz i wykonaj `up -d`; mikroserwisy nie mają montowania kodu z hosta |
| Zmiana `.env` niewidoczna | Wykonaj `up -d`, nie tylko restart |
| Nie działa hasło z `.env` | Konto mogło już istnieć; seed nie resetuje hasła. Ustaw nowe w administracji |
| users kończy start po konfiguracji pracownika | Sprawdź kompletność `DJANGO_EMPLOYEE_*` i kolizję loginu z inną rolą |
| Zmiana DB_PASS nie zmieniła hasła bazy | Zmienne inicjalizacji PostgreSQL nie zmieniają automatycznie kont istniejącego wolumenu |
| Brak usług po utracie katalogu Consula | Uruchom Consul i zrestartuj osiem usług, aby ponownie się zarejestrowały |
| Rezerwacja jest pending_retry | Sprawdź notifications i reservation-worker; wniosek jest już zapisany |
| Decyzja jest blocked | Sprawdź decyzję, jej last_error i aktualny status rezerwacji; nie ma automatycznej naprawy konfliktu |
| Brak e-mail mimo sent | Sprawdź konsolowy backend, adres odbiorcy i przypisanie opiekuna |
| Node.js 14 nie buduje frontendu | Użyj Node.js 22.12+ albo kompilacji Docker |

Ponowna rejestracja po utracie katalogu:

```bash
docker compose restart users rooms guardians reservations decisions notifications search reports
```

`docker compose config` pokazuje rozwiniętą konfigurację, w tym wartości środowiska.
Nie publikuj jej pełnego wyniku z sekretami w zgłoszeniach i dokumentacji.

## 11 Opcjonalne komponenty i granice wdrożenia

```bash
docker compose --profile tools up -d pgadmin
docker compose --profile legacy up -d legacy-web
docker compose --profile legacy-portal up -d portal
```

`legacy-web` jest monolitem na porcie 8001 i nie korzysta z nowych schematów usług.
Portal techniczny ma trasę o niższym priorytecie niż frontend React; jego uruchomienie
nie zastępuje domyślnej strony React. Katalogi legacy pozostają dla porównania i historii.

Przed udostępnieniem aplikacji poza lokalnym środowiskiem potrzebne są m.in. TLS,
ochrona panelu Consula, kontrola dostępu do wewnętrznego API, odpowiedni serwer Django,
ograniczenie odczytu prywatnych rezerwacji i osobne uprawnienia bazy. Obecne mapowania
portów Compose nie ograniczają nasłuchiwania do 127.0.0.1.

Opis architektury i ograniczeń: [dokumentacja projektu](dokumentacja.md).
Składnia uruchamiania poleceń w kontenerze: [Docker Compose exec](https://docs.docker.com/reference/cli/docker/compose/exec/).
