# Wymagania wstępne i konfiguracja poczty e-mail

Przed włączeniem pakietu poczty e-mail upewnij się, że Twoje środowisko i konto Cloudflare są prawidłowo skonfigurowane.

## Wymagania Cloudflare

1.  **Zarządzanie domeną:** Twoja domena musi być aktywna w Cloudflare.
2.  **Email Routing (Przychodzący):** Cloudflare Email Routing jest dostępny na wszystkich planach, w tym bezpłatnym. DockFlare automatycznie konfiguruje wymagane rekordy MX, SPF i DMARC.
3.  **Email Sending (Wychodzący):** Cloudflare Email Sending jest obecnie w fazie Beta. DockFlare automatycznie konfiguruje rekordy podpisu DKIM i subdomenę wysyłki. Jednak wysyłanie na zewnętrzne adresy wymaga:
    - **Cloudflare Workers Paid Plan** (5 $/miesiąc).
    - Ręcznej aktywacji **CF Email Sending (Beta)** w panelu Cloudflare w sekcji **Email → Email Sending**.
    - Bez tych kroków poczta wychodząca jest ograniczona wyłącznie do zweryfikowanych adresów Cloudflare.
4.  **Magazyn R2:** R2 musi być włączony w panelu Cloudflare. R2 obejmuje bezpłatny poziom 10 GB, ale może być konieczne dodanie metody płatności w celu jego aktywacji.

## Uprawnienia tokenu API

Pakiet poczty e-mail wymaga dodatkowych uprawnień w istniejącym tokenie API DockFlare. Zaktualizuj go w **Profil użytkownika > Tokeny API**, dodając następujące uprawnienia:

| Zakres | Konkretne uprawnienie | Poziom dostępu | Cel |
| :--- | :--- | :--- | :--- |
| **Konto** | **Workers Scripts** | **Edycja** | Wdrażanie workerów przychodzących/wychodzących |
| **Konto** | **Workers KV Storage** | **Edycja** | Egzekwowanie limitów w czasie rzeczywistym na brzegu sieci |
| **Konto** | **R2 Storage** | **Edycja** | Tworzenie i zarządzanie zasobnikami tranzytowymi |
| **Konto** | **Access: Apps and Policies** | **Edycja** | Tworzenie obejścia dla ścieżki webhooka przychodzącej poczty, gdy Webmail jest chroniony przez Cloudflare Access |
| **Strefa** | **Email Routing** | **Edycja** | Aktywacja routingu i zarządzanie regułami |
| **Strefa** | **DNS** | **Edycja** | Tworzenie rekordów MX, SPF, DMARC i DKIM |

> **Uwaga dotycząca bezpieczeństwa:** Zdecydowanie zaleca się ograniczenie „Zasobów konta" i „Zasobów strefy" tego tokenu wyłącznie do konkretnego konta i domen, których zamierzasz używać z DockFlare.

## Wymagania systemowe

*   **DockFlare:** v3.1.0 lub nowszy.
*   **Docker:** v20.10+.
*   **Docker Compose:** v2.20+ (wymagany dla obsługi `profiles`).
*   **Przestrzeń dyskowa:** Upewnij się, że na maszynie hosta jest wystarczająco miejsca na wolumen `mail_data`, który będzie przechowywać wszystkie bazy danych poczty e-mail i załączniki.
