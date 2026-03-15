# Przełączanie pomiędzy trybami

W dowolnym momencie możesz przełączać DockFlare pomiędzy trybem **Wewnętrznym** (domyślnym) i **Zewnętrznym** `cloudflared`. W tym przewodniku opisano proces płynnego przejścia.

Szczegółowe porównanie tych dwóch trybów można znaleźć na stronie [Wewnętrzny i zewnętrzny `cloudflared`](Internal-vs-External-cloudflared.md).

---

## Przełączanie z trybu wewnętrznego na zewnętrzny

Ten proces obejmuje skonfigurowanie własnego agenta `cloudflared`, a następnie polecenie DockFlare, aby go używał.

**Krok 1: Skonfiguruj zewnętrznego agenta `cloudflared`**

Najpierw musisz skonfigurować i uruchomić własnego agenta `cloudflared`. Może to być proces w systemie operacyjnym hosta lub innym kontenerze Docker.

* Upewnij się, że jest skonfigurowany do korzystania z określonego tunelu Cloudflare.
* Zanotuj **ID tunelu** (UUID).
* Uruchom agenta i potwierdź, że działa poprawnie i jest wyświetlany jako „połączony” na pulpicie nawigacyjnym Cloudflare.

**Krok 2: Skonfiguruj ponownie i uruchom ponownie DockFlare**

Następnie musisz zaktualizować zmienne środowiskowe kontenera DockFlare, aby poinformować go o konieczności przejścia do trybu zewnętrznego.

W swoim `docker-compose.yml`:
```yaml
services:
  dockflare:
    image: alplat/dockflare:stable
    # ... other settings
    environment:
      # Enable external mode
      - USE_EXTERNAL_CLOUDFLARED=true
      # Provide the ID of your running tunnel
      - EXTERNAL_TUNNEL_ID=your-tunnel-uuid-goes-here
```

**Krok 3: Wdróż zmianę**

Uruchom `docker compose up -d`, aby odtworzyć kontener DockFlare z nowymi zmiennymi środowiskowymi.

Po uruchomieniu zaktualizowanego kontenera DockFlare:
1. Wykryje, że `USE_EXTERNAL_CLOUDFLARED` to `true`.
2. **zatrzyma i usunie** własny zarządzany kontener `cloudflared-agent`.
3. Rozpocznie wysyłanie wszystkich konfiguracji reguł ingress do tunelu określonego przez `EXTERNAL_TUNNEL_ID`.

Twoje usługi będą teraz świadczone przez zarządzanego zewnętrznie agenta `cloudflared`.

---

## Przełączanie z trybu zewnętrznego na tryb wewnętrzny

Ten proces jest prostszy, ponieważ pozwala DockFlare przejąć kontrolę.

**Krok 1: Skonfiguruj ponownie DockFlare**

Usuń zmienne środowiskowe trybu zewnętrznego z pliku DockFlare `docker-compose.yml`.

```yaml
services:
  dockflare:
    image: alplat/dockflare:stable
    # ... other settings
    environment:
      # Remove the following two lines
      # - USE_EXTERNAL_CLOUDFLARED=true
      # - EXTERNAL_TUNNEL_ID=your-tunnel-uuid-goes-here
```

**Krok 2: Wdróż zmianę**

Uruchom `docker compose up -d`, aby odtworzyć kontener DockFlare.

Po uruchomieniu zaktualizowanego kontenera DockFlare:
1. Wykryje, że `USE_EXTERNAL_CLOUDFLARED` to `false`.
2. Automatycznie **utworzy, skonfiguruje i uruchomi** swój własny wewnętrzny kontener `cloudflared-agent`.
3. Skonfiguruje nowego agenta tak, aby używał nazwy tunelu zdefiniowanej w ustawieniach DockFlare.

**Krok 3: Zlikwiduj swojego agenta zewnętrznego**

Po potwierdzeniu, że nowy agent wewnętrzny działa poprawnie i obsługuje ruch, możesz bezpiecznie zatrzymać i usunąć własnego agenta `cloudflared`.
