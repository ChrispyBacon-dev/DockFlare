# Polityka bezpieczeństwa treści (CSP)

## Co to jest polityka bezpieczeństwa treści?

Polityka bezpieczeństwa treści (CSP) to standard bezpieczeństwa sieciowego, który pomaga zapobiegać niektórym typom ataków, w szczególności atakom typu Cross-Site Scripting (XSS) i wstrzykiwaniu danych. Działa poprzez informowanie przeglądarki, które źródła treści (skrypty, style, obrazy itp.) są zaufane i mogą być ładowane na stronie internetowej.

## CSP DockFlare

Sama aplikacja DockFlare ma panel administracyjny. Aby go chronić, DockFlare stosuje ścisłą politykę bezpieczeństwa treści (CSP) we własnym interfejsie.

Jest to ważna funkcja bezpieczeństwa wewnętrznego, zaprojektowana w celu ochrony Ciebie, administratora, przed potencjalnymi lukami w zabezpieczeniach przeglądarki podczas korzystania z pulpitu nawigacyjnego DockFlare.

## Zakres CSP

Ważne jest, aby zrozumieć, że CSP DockFlare ma zastosowanie **tylko do panelu administracyjnego DockFlare**.

**Nie** ma to wpływu, nie modyfikuje ani nie dodaje żadnych nagłówków CSP do ruchu przesyłanego przez tunel Cloudflare do Twoich własnych aplikacji. Jeśli chcesz zaimplementować CSP we własnych aplikacjach, musisz to skonfigurować w samych aplikacjach (np. ustawiając nagłówek HTTP `Content-Security-Policy` na serwerze WWW lub w kodzie aplikacji).

## Konfiguracja

CSP DockFlare stanowi integralną część jego profilu bezpieczeństwa i **nie jest konfigurowalny przez użytkownika**. Zasady są tak dobrane, aby były możliwie restrykcyjne, a jednocześnie pozwalały panelowi działać prawidłowo.

Jeśli chcesz dowiedzieć się więcej o tym, jak ogólnie działają zasady bezpieczeństwa treści, doskonałym źródłem informacji jest [Dokumenty internetowe MDN dotyczące CSP](https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP).
