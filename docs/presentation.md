# Prezentacja demonstracyjna

1. **Problem:** osobne zarządzanie salami, opiekunami i rezerwacjami.
2. **Architektura:** osiem usług Django, frontend React + PrimeReact, Consul, Traefik i PostgreSQL.
3. **Własność danych:** oddzielny schemat na usługę; komunikacja przez REST.
4. **Demo:** wyszukiwarka i kalendarz bez logowania; logowanie administratora, utworzenie sali i konta pracownika.
5. **Demo:** przypisanie opiekuna, rezerwacja i blokada konfliktu.
6. **Demo:** decyzja opiekuna, historia powiadomień i raport.
7. **Odporność:** wyłączona usługa powiadomień zostawia zdarzenie do ponowienia.
8. **Wnioski:** sześć tematów obowiązkowych z instrukcji i ograniczenia demonstracji.

Do pokazania działania można uruchomić `python scripts/smoke_microservices.py`
oraz otworzyć `http://localhost:8002/` i panel Consul `http://localhost:8500/`.
