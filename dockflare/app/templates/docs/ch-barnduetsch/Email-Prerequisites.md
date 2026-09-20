# E-Mail-Voraussetzige & Istellig

Bevor du d E-Mail-Suite aktiviersch, stell sicher, dass dini Umgebig u dis Cloudflare-Konto richtig konfiguriert sind.

## Cloudflare-Aaforderige

1.  **Domain-Verwaltig:** Dini Domain muss i Cloudflare aktiv sii.
2.  **Email Routing:** D Domain muss für Cloudflare Email Routing berechtigt sii (verfügbar uf de meischte Pläng, au uf em Free-Plan) u für Cloudflare Email Sending (Beta-Zuegäng für usgehendi Post nötig).
3.  **R2-Spycher:** R2 muss i dim Cloudflare-Dashboard aktiviert sii. R2 beinhaltet es gratis Kontingent vo 10 GB, aber zur Aktivierig chasch es Zahlungsmittel bruuche.

## API-Token-Berechtigunge

D E-Mail-Suite bruucht zusätzlichi Berechtigunge uf dim bestehende DockFlare-API-Token. Aktualisier ihn under **Benutzerprofil > API-Token** u füeg d folgendi Berechtigunge zue:

| Bereich | Spezifischi Berechtigung | Zugriffsebeni | Zweck |
| :--- | :--- | :--- | :--- |
| **Account** | **Workers Scripts** | **Bearbeite** | Inbound-/Outbound-Worker deploye |
| **Account** | **Workers KV Storage** | **Bearbeite** | Echtzeit-Quota-Durchsetzung am Edge |
| **Account** | **R2 Storage** | **Bearbeite** | Transit-Buckets erstelle u verwalte |
| **Account** | **Access: Apps and Policies** | **Bearbeite** | Es Umgehig für de Iigang-Mail-Webhook-Pfad erstelle, wenn Webmail dür Cloudflare Access gschützt isch |
| **Zone** | **Email Routing** | **Bearbeite** | Routing aktiviere u Regle verwalte |
| **Zone** | **DNS** | **Bearbeite** | MX-, SPF-, DMARC- u DKIM-Iiträg erstelle |

> **Sicherheitshinwys:** Es wird dringend empfohle, d „Account Resources" u „Zone Resources" vo däm Token nur uf s spezifischi Konto u d Domains z beschränke, wo du mit DockFlare verwende möchtisch.

## Systemvoraussetzige

*   **DockFlare:** v3.1.0 oder neuer.
*   **Docker:** v20.10+.
*   **Docker Compose:** v2.20+ (für `profiles`-Unterstützig nötig).
*   **Spycherplatz:** Stell sicher, dass uf em Host-System gnueg Platz für s `mail_data`-Volume vorhanden isch, wo alli E-Mail-Datebanke u Ahäng spicheret.
