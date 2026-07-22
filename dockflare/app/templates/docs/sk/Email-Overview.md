# Prehľad e-mailovej sady

DockFlare Email je plne samostatne hostovaný, suverénny e-mailový systém postavený na tvojej existujúcej infraštruktúre DockFlare. Je navrhnutý tak, aby ponúkol pohodlie cloudového e-mailu so súkromím a kontrolou samostatného hostovania.

## Koncept suverénneho e-mailu

Samostatné hostovanie e-mailu je tradične náročné pre „blacklisting domácich IP adries“, keď hlavní e-mailoví poskytovatelia blokujú rezidenčné IP adresy. DockFlare to rieši tak, že Cloudflare používa ako **bezstavovú doručovaciu sieť**:

1.  **Cloudflare** zvláda náročnú prácu s SMTP doručovaním, MX routingom a dočasným bufferovaním.
2.  **DockFlare** vlastní dáta. Tvoje správy, prílohy a konfigurácie schránok sú uložené na tvojom vlastnom hardvéri.

Na infraštruktúre Cloudflare nezostáva žiadny obsah e-mailov. Počas prenosu sa nakrátko nabufferuje v R2 buckete a hneď po spracovaní tvojím lokálnym Mail Managerom sa odstráni.

## Architektúra

Systém pozostáva z viacerých integrovaných komponentov:

*   **Prichádzajúci tok:** Internet → Cloudflare Email Routing → inbound worker → R2 buffer → webhook DockFlare Mail Managera → lokálne úložisko.
*   **Odchádzajúci tok:** rozhranie webmailu → API Mail Managera → outbound worker → Cloudflare `send_email` → internet.
*   **Suverenita dát:** Všetky e-maily sa parsujú a ukladajú do lokálnej SQLite databázy, prílohy sa ukladajú do tvojho lokálneho súborového systému.

## Odosielanie pošty — plány a obmedzenia

Cloudflare Email Sending (Beta) má dve úrovne podľa tvojho Cloudflare plánu:

| Cieľ odosielania | Free plán | Workers Paid plán ($5/mes) |
| :--- | :--- | :--- |
| Overené Cloudflare adresy (adresy potvrdené v tvojom CF účte) | ✅ Povolené | ✅ Povolené |
| Ľubovoľná externá adresa | ❌ Nepovolené | ✅ Povolené |

DockFlare počas nastavenia domény automaticky pripraví DKIM podpisové záznamy a odosielaciu subdoménu (`mail.tvojadomena.com`). **Plné externé odosielanie si však vyžaduje dva ďalšie manuálne kroky**:

1. **Prejdi na Cloudflare Workers Paid Plan** — dostupný za $5/mesiac v tvojom Cloudflare dashboarde.
2. **Aktivuj CF Email Sending (Beta)** — prejdi na [Cloudflare Dashboard → Email → Email Sending](https://dash.cloudflare.com/) a zapni túto funkciu pre svoj účet.

Kým tieto kroky nedokončíš, odchádzajúca pošta z tvojho webmailového klienta sa doručí len na e-mailové adresy overené v tvojom Cloudflare účte. Štítok stavu domény na stránke Správa e-mailov v DockFlare odzrkadľuje, či je DKIM nakonfigurovaný (`Odosielanie: Aktívne`) alebo ešte nie (`Odosielanie: Čaká`).

## Kľúčové funkcie

*   **Podpora viacerých domén:** Hostuj e-mail pre toľko domén, koľko spravuješ v Cloudflare.
*   **Vynucovanie kvót na edge:** Plná schránka? Cloudflare workeri odmietnu e-mail na úrovni SMTP (5.2.2) ešte predtým, než sa dostane na tvoj server, čím šetria prenos dát.
*   **Fulltextové vyhľadávanie:** Bleskovo rýchle vyhľadávanie naprieč všetkými e-mailmi pomocou SQLite FTS5.
*   **Súkromie na prvom mieste:** Všetky interakcie s API používajú EdDSA JWT overovanie. HTML obsah e-mailov sa pred vykreslením sanitizuje, aby sa predišlo XSS a sledovacím pixelom.
*   **PWA webmail:** Moderný, mobilne responzívny webmailový klient, ktorý si nainštaluješ na mobil alebo počítač.
*   **Push notifikácie:** Dostávaj upozornenia na novú poštu v reálnom čase cez Web Push (VAPID).
*   **Odolnosť:** Ak server prejde do offline, Cloudflare R2 nabufferuje prichádzajúcu poštu a automaticky sa každých 5 minút pokúša o doručenie.
