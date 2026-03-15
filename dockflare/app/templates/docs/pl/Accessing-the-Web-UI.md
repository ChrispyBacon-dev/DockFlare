# Dostęp do panelu administracyjnego

Po pomyślnym uruchomieniu kontenera DockFlare możesz otworzyć panel administracyjny, aby zarządzać ustawieniami, sprawdzać stan tuneli i ręcznie konfigurować reguły ingress.

## Domyślny adres URL

Domyślnie panel administracyjny DockFlare jest dostępny na porcie `5000`. Otwórz przeglądarkę i przejdź pod adres:

```
http://<your-server-ip>:5000
```

Zastąp `<your-server-ip>` adresem IP serwera, na którym działa DockFlare.

## Pierwsza konfiguracja

Przy pierwszym wejściu do panelu administracyjnego uruchomi się **kreator konfiguracji początkowej**. Pomoże on:

1. Przywróć dane z istniejącego archiwum kopii zapasowej DockFlare (`dockflare_backup_*.zip`). Jeśli wybierzesz tę opcję, system zaimportuje zaszyfrowane klucze konfiguracji, stanu i agenta, a następnie automatycznie zrestartuje kontener, aby je zastosować.
2. Utworzyć konto administratora i hasło do panelu administracyjnego.
3. Podaj swój identyfikator konta Cloudflare, identyfikator strefy (opcjonalnie) i token API.
4. Potwierdź ustawienia tunelu i zakończ kroki wprowadzające.

## Logowanie

Po zakończeniu konfiguracji przy każdym wejściu do panelu administracyjnego zobaczysz ekran logowania. Użyj hasła utworzonego podczas konfiguracji.

## Wyłączanie logowania za pomocą hasła

DockFlare zawiera ustawienie „Wyłącz logowanie hasłem” przeznaczone do zaawansowanych wdrożeń, w których sam DockFlare jest chroniony przez zewnętrzną warstwę uwierzytelniania (np. Cloudflare Access). **Zdecydowanie odradzamy używanie tej funkcji** w przypadku większości wdrożeń.

### Dlaczego to ustawienie istnieje

Jeśli uruchomisz DockFlare za Cloudflare Access lub innym serwerem proxy uwierzytelniania, który wymusza logowanie jednokrotne przed dotarciem do aplikacji, możesz wyłączyć wbudowane hasło logowania DockFlare, aby uniknąć podwójnego uwierzytelniania.

### Zagrożenia bezpieczeństwa, gdy jest włączone

- ⚠️ **Wszystkie punkty końcowe API stają się dostępne bez uwierzytelniania**, gdy to ustawienie jest włączone
- ⚠️ **Ekspozycja sieci Docker:** Nawet jeśli DockFlare stoi za Cloudflare Access w publicznym Internecie, kontenery w tej samej sieci Docker mogą ominąć uwierzytelnianie zewnętrzne i uzyskać bezpośredni dostęp do API DockFlare
- ⚠️ **Brak wymuszania uwierzytelniania:** Aplikacja zakłada, że uwierzytelnianie zewnętrzne obsługuje bezpieczeństwo

### Przykład wektora ataku

```
Internet → Cloudflare Access (Protected) → DockFlare ✅
         ↓
Docker Network → Other Container → DockFlare API (Unprotected) ❌
```

Nawet jeśli DockFlare jest chroniony przez Cloudflare Access z Internetu, każdy kontener działający w tej samej sieci Docker może ominąć tę ochronę i uzyskać bezpośredni dostęp do punktów końcowych API DockFlare bez uwierzytelniania.

### Zalecane podejście

Zamiast wyłączać uwierzytelnianie hasłem, użyj jednej z następujących bezpiecznych opcji:

1. **Lokalne dane uwierzytelniające DockFlare** – Proste uwierzytelnianie hasłem wbudowane w DockFlare
2. **Dostawcy OAuth/OIDC** — skonfiguruj Google, GitHub, Azure AD lub innych dostawców tożsamości, aby ułatwić jednokrotne logowanie bez poświęcania bezpieczeństwa (zobacz [Konfiguracja dostawcy OAuth](OAuth-Provider-Setup.md))

Obie opcje zapewniają prawidłowe uwierzytelnienie przy zachowaniu wygody SSO. Opcja OAuth umożliwia jednokrotne logowanie bez zagrożeń bezpieczeństwa wynikających z wyłączonego uwierzytelniania.

### Podsumowanie

Jeśli nie masz bardzo specyficznej, dobrze zrozumiałej architektury bezpieczeństwa z izolacją sieci, włącz logowanie za pomocą hasła i dla wygody używaj protokołu OAuth.
