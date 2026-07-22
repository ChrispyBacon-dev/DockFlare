# Interný vs. externý `cloudflared`

DockFlare dokáže spravovať agenta `cloudflared` v dvoch režimoch — je to softvér, ktorý reálne vytvára trvalé spojenie medzi tvojím serverom a sieťou Cloudflare. Pochopenie týchto dvoch režimov je kľúčom k výberu správneho nastavenia pre tvoje prostredie.

## Interný režim (predvolený)

V internom režime preberá DockFlare plnú zodpovednosť za správu agenta `cloudflared`.

### Ako to funguje
Keď DockFlare naštartuje, automaticky:
1.  Vytvorí vyhradený Docker kontajner s image `cloudflare/cloudflared`.
2.  Nakonfiguruje tento agentský kontajner tak, aby sa pripojil k tvojmu Cloudflare účtu a použil tunel zadaný v nastaveniach DockFlare.
3.  Zabezpečí, že agent beží, a reštartuje ho, ak zlyhá.
4.  Automaticky uplatní všetky relevantné nastavenia, napríklad zapnutie Prometheus metrics endpointu.

Toto je **predvolený a odporúčaný** režim pre väčšinu používateľov.

### Výhody
*   **Jednoduchosť:** Nastavenie bez konfigurácie. DockFlare za teba zvláda všetko.
*   **Zaručená kompatibilita:** DockFlare zabezpečí, že agent je nakonfigurovaný tak, aby s ním vedel spolupracovať.
*   **Centralizovaná správa:** Všetko okolo tvojich tunelov spravuje DockFlare.

### Nevýhody
*   **Menšia kontrola:** Nad konfiguráciou agenta `cloudflared` máš len obmedzenú kontrolu, obmedzenú na to, čo DockFlare sprístupňuje.

---

## Externý režim `cloudflared`

V externom režime za beh a správu agenta `cloudflared` zodpovedáš ty. DockFlare sa pripojí k tomuto existujúcemu agentovi namiesto toho, aby vytváral vlastného.

### Ako to funguje
DockFlare **nevytvorí** kontajner `cloudflared`. Namiesto toho predpokladá, že máš niekde bežiaceho agenta `cloudflared`, ktorého môže použiť. Môže to byť:
*   Proces `cloudflared` bežiaci priamo na hostiteľskom OS (napr. ako `systemd` služba).
*   Kontajner `cloudflared`, ktorý spravuješ sám samostatným súborom `docker-compose.yml` alebo príkazom Docker run.
*   Agent `cloudflared` bežiaci na úplne inom stroji.

Ide o **pokročilý režim** určený pre používateľov s konkrétnymi potrebami alebo zložitými existujúcimi nastaveniami.

### Výhody
*   **Maximálna kontrola:** Máš plnú kontrolu nad agentom `cloudflared` vrátane jeho verzie, argumentov príkazového riadka a životného cyklu.
*   **Integrácia s existujúcimi nastaveniami:** Ideálne, ak už máš agenta `cloudflared` bežiaceho na iné účely.
*   **Oddelenie:** Oddeľuje životný cyklus DockFlare od životného cyklu agenta `cloudflared`.

### Nevýhody
*   **Zložitosť:** Ty zodpovedáš za to, že agent `cloudflared` beží, je správne nakonfigurovaný a pripojený k správnemu tunelu.
*   **Réžia konfigurácie:** Musíš nakonfigurovať DockFlare na použitie tohto externého agenta.

### Ako zapnúť externý režim
Na zapnutie externého režimu musíš pre DockFlare kontajner nastaviť tieto premenné prostredia:

*   `USE_EXTERNAL_CLOUDFLARED=true`: Zapne externý režim.
*   `EXTERNAL_TUNNEL_ID`: Musí byť nastavené na UUID tunela, ktorý tvoj externý agent `cloudflared` používa.

Keď sú tieto premenné nastavené, DockFlare preskočí svoju internú správu agenta a namiesto toho pošle všetky konfigurácie ingress pravidiel tunelu zadanému cez `EXTERNAL_TUNNEL_ID`.
