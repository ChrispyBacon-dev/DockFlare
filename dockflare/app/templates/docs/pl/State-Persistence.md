# Trwałość stanu

DockFlare to aplikacja stanowa. Musi śledzić usługi, którymi zarządza, zastąpienia interfejsu użytkownika i inne szczegóły konfiguracji. Ten stan jest utrwalany na dysku, aby mieć pewność, że konfiguracja nie zostanie utracona w przypadku ponownego uruchomienia lub ponownego utworzenia kontenera DockFlare.

## Jak przechowywany jest stan

DockFlare przechowuje swój stan w trzech kluczowych plikach znajdujących się w katalogu `/app/data` wewnątrz kontenera:

1. `dockflare_config.dat`: To jest najbardziej krytyczny plik. Zawiera wszystkie podstawowe ustawienia i poufne informacje w **zaszyfrowanym** formacie. Obejmuje to:
    * Twój token API Cloudflare i identyfikator konta.
    * Skrót hasła do panelu administracyjnego DockFlare.
    * Podstawowe ustawienia konfigurowane w panelu, takie jak nazwa tunelu i identyfikatory stref.

2. `agent_keys.dat`: Zaszyfrowany magazyn zawierający wszystkie klucze API agenta i ich metadane (właściciel, status, znaczniki czasu). Dbanie o bezpieczeństwo tego pliku zapobiega ponownemu użyciu nieaktualnych kluczy.

3. `state.json`: Ten plik przechowuje dynamiczny stan usług zarządzanych w zwykłym formacie JSON. Obejmuje to:
    * Lista wszystkich reguł ingress zarządzanych przez DockFlare, niezależnie od tego, czy pochodzą z etykiet Dockera, czy zostały utworzone ręcznie w panelu administracyjnym.
    * Wszelkie nadpisania interfejsu zastosowane do zasad dostępu.
    * Wszystkie utworzone przez Ciebie grupy dostępu.
    * Status `pending_deletion` dla usług, które zostały zatrzymane, ale nadal są w okresie karencji.

## Znaczenie trwałego wolumenu

Ponieważ cała konfiguracja jest przechowywana w katalogu `/app/data`, **absolutnie istotne** jest zamapowanie tego katalogu na stały wolumin na komputerze hosta.

Jeśli nie używasz trwałego woluminu, **wszystkie ustawienia, hasło do panelu administracyjnego i konfiguracje reguł zostaną utracone** za każdym razem, gdy kontener DockFlare zostanie usunięty i utworzony ponownie.

### Zalecana konfiguracja Docker Compose

Zalecana konfiguracja `docker-compose.yml` obsługuje to automatycznie, definiując nazwany wolumin i montując go w `/app/data`:

```yaml
services:
  dockflare:
    # ... other settings
    volumes:
      # This line ensures your data is persisted
      - ./dockflare_data:/app/data

volumes:
  # This defines the named volume on your host
  dockflare_data:
```

Dzięki tej konfiguracji pliki `dockflare_config.dat`, `agent_keys.dat` i `state.json` będą przechowywane w katalogu o nazwie `dockflare_data` na hoście, bezpiecznie zachowując konfigurację podczas aktualizacji kontenera.

## Kopia zapasowa i przywracanie

DockFlare łączy teraz wszystkie krytyczne dane w jedno zaszyfrowane archiwum kopii zapasowych. Pamięci podręczne Redis są pomijane, ponieważ można je bezpiecznie odbudować w prywatnej sieci `dockflare-internal`. Panel **Ustawienia → Kopia zapasowa i przywracanie** umożliwia pobranie kodu `.zip` zawierającego:

* `dockflare_config.dat`
* `dockflare.key`
* `agent_keys.dat`
* `state.json` (jeśli występuje)
* Manifest z sumami kontrolnymi do weryfikacji integralności

Przywrócenie archiwum powoduje odtworzenie tych plików i ponowne załadowanie ich do działającej instancji. Przesyłanie starszej wersji `state.json` jest nadal akceptowane, ale przywraca jedynie metadane reguły — później konieczne będzie ponowne ręczne wprowadzenie danych uwierzytelniających.
DockFlare automatycznie uruchamia ponownie kontener po pełnym przywróceniu archiwum, dzięki czemu zaszyfrowana konfiguracja zostaje natychmiast załadowana.
