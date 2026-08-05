# Predpoklady a nastavenie e-mailu

Skôr než zapneš e-mailovú sadu, uisti sa, že tvoje prostredie a Cloudflare účet sú správne nakonfigurované.

## Požiadavky Cloudflare

1.  **Správa domény:** Tvoja doména musí byť v Cloudflare aktívna.
2.  **Email Routing (prichádzajúca pošta):** Cloudflare Email Routing je dostupné vo všetkých plánoch vrátane Free. DockFlare automaticky nakonfiguruje potrebné MX, SPF a DMARC záznamy.
3.  **Odosielanie e-mailov (odchádzajúca pošta):** Cloudflare Email Sending je momentálne v Bete. DockFlare automaticky nakonfiguruje DKIM podpisové záznamy a odosielaciu subdoménu. Odosielanie na externé adresy si však vyžaduje:
    - **Cloudflare Workers Paid Plan** ($5/mesiac).
    - Manuálnu aktiváciu **CF Email Sending (Beta)** v Cloudflare dashboarde pod **Email → Email Sending**.
    - Bez týchto krokov je odchádzajúca pošta obmedzená len na overené Cloudflare adresy.
4.  **R2 Storage:** V Cloudflare dashboarde musíš mať zapnuté R2. R2 zahŕňa bezplatnú vrstvu 10 GB, no na jej aktiváciu možno budeš musieť do účtu pridať platobnú metódu.

## Oprávnenia API tokenu

E-mailová sada si vyžaduje ďalšie oprávnenia na tvojom existujúcom DockFlare API tokene. Aktualizuj ho v **User Profile > API Tokens** a pridaj tieto oprávnenia:

| Rozsah | Konkrétne oprávnenie | Úroveň prístupu | Účel |
| :--- | :--- | :--- | :--- |
| **Account** | **Workers Scripts** | **Edit** | Nasadenie inbound/outbound workerov |
| **Account** | **Workers KV Storage** | **Edit** | Vynucovanie kvót v reálnom čase na edge |
| **Account** | **R2 Storage** | **Edit** | Vytváranie a správa tranzitných bucketov |
| **Zone** | **Email Routing** | **Edit** | Aktivácia routingu a správa pravidiel |
| **Zone** | **DNS** | **Edit** | Vytváranie MX, SPF, DMARC a DKIM záznamov |

> **Bezpečnostná poznámka:** Dôrazne odporúčame obmedziť „Account Resources“ a „Zone Resources“ tohto tokenu len na konkrétny účet a domény, ktoré plánuješ používať s DockFlare.

## Systémové požiadavky

*   **DockFlare:** v3.1.0 alebo novší.
*   **Docker:** v20.10+.
*   **Docker Compose:** v2.20+ (potrebné pre podporu `profiles`).
*   **Úložisko:** Uisti sa, že máš na hostiteľskom stroji dosť miesta na disku pre volume `mail_data`, kde sa uložia všetky e-mailové databázy a prílohy.
