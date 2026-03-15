# Korzystanie z wielu domen (indeksowane etykiety)

DockFlare udostępnia funkcję **indeksowanych etykiet**, która umożliwia zdefiniowanie wielu niezależnych reguł ingress dla pojedynczego kontenera. Jest to szczególnie przydatne, gdy chcesz udostępnić różne porty lub ścieżki tej samej usługi pod różnymi publicznymi nazwami hostów.

## Jak to działa

Aby utworzyć wiele reguł, wystarczy poprzedzić standardowe etykiety DockFlare liczbą całkowitą i kropką, zaczynając od `0`. Na przykład `dockflare.0.hostname`, `dockflare.1.hostname` i tak dalej.

* Każdy indeks (np. `0`, `1`, `2`) reprezentuje osobną regułę ingress.
* Indeksowana nazwa hosta (np. `dockflare.<index>.hostname`) jest zawsze wymagana do zainicjowania nowej reguły.
* Inne etykiety o tym samym indeksie (np. `dockflare.<index>.service`) będą miały zastosowanie tylko do tej konkretnej reguły.

## Mechanizm awaryjny

Kluczową cechą etykiet indeksowanych jest mechanizm awaryjny. Jeśli nie podasz konkretnej indeksowanej etykiety dla reguły, **powróci ona do wartości odpowiedniej etykiety podstawowej (nieindeksowanej)**.

Umożliwia to zdefiniowanie wspólnych ustawień raz na poziomie podstawowym i zastąpienie tylko określonych wartości, które należy zmienić dla każdej indeksowanej reguły.

## Przykład: udostępnianie interfejsu WWW i API

Załóżmy, że masz pojedynczy kontener, który obsługuje zarówno aplikację internetową na porcie `80`, jak i oddzielne API na porcie `3000`. Chcesz je udostępnić odpowiednio w `app.example.com` i `api.example.com`. Chcesz także zabezpieczyć interfejs API określoną grupą dostępu, podczas gdy główna aplikacja pozostaje publiczna.

Oto jak można to skonfigurować za pomocą indeksowanych etykiet:

```yaml
services:
  my-app:
    image: my-application
    restart: unless-stopped
    networks:
      - cloudflare-net
    labels:
      - "dockflare.enable=true"

      # --- Base Labels (Fallback) ---
      # This service is used by rule 0, as it's not specified there.
      - "dockflare.service=http://my-app:80" 

      # --- Rule 0: Główny interfejs WWW ---
      - "dockflare.0.hostname=app.example.com"
      # No 'service' label here, so it falls back to the base one.
      # No 'access.group' label, so it's public.

      # --- Rule 1: The API ---
      - "dockflare.1.hostname=api.example.com"
      # Override the service to point to the API port.
      - "dockflare.1.service=http://my-app:3000"
      # Add a specific access policy for this rule only.
      - "dockflare.1.access.group=api-users-policy"
```

### Podział przykładu

* **Zasada 0 (`app.example.com`)**:
    * Definiuje `dockflare.0.hostname`.
    * Nie definiuje `dockflare.0.service`, więc wraca do podstawy `dockflare.service` i używa `http://my-app:80`.
    * Jest to usługa publiczna, ponieważ dla tego indeksu ani na poziomie podstawowym nie zdefiniowano żadnej polityki dostępu.

* **Zasada 1 (`api.example.com`)**:
    * Definiuje `dockflare.1.hostname`.
    * **Zastępuje** usługę kodem `dockflare.1.service`, wskazując port API `3000`.
    * Stosuje określoną politykę bezpieczeństwa przy użyciu `dockflare.1.access.group`. Ta etykieta ma wpływ tylko na tę regułę.

Takie podejście pozwala zachować przejrzystość konfiguracji etykiet i uniknąć powtórzeń, dzięki czemu pliki `docker-compose.yml` są łatwiejsze do odczytania i konserwacji.
