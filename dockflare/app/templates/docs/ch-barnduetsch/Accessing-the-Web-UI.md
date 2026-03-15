# Zuegriff uf d Web UI

Sobald dr DockFlare-Container louft, chasch über d Web UI dini Iistellige verwalte, Tunnel überwache u Regle manuell aapasse.

## Standard-URL

Standardmässig isch d DockFlare Web UI über Port `5000` erreichbar. Mach im Browser die URL uf:

```
http://<your-server-ip>:5000
```

Ersetz `<your-server-ip>` durch d IP-Adräss vom Server, wo DockFlare druf louft.

## Erstiirichtig

Biim erschte Ufruef führt di dr **Erstiirichtigs-Assistent** dür d Konfiguration.

D Schritte sy normalerwys:

1. Optional es vorhandes DockFlare-Backup wiederhärstelle (`dockflare_backup_*.zip`)
2. Es Admin-Konto u es Passwort für d Web UI aalege
3. Dini Cloudflare-Account-ID, optional d Zone-ID u dr API-Token aagee
4. D Tunnel-Iistellige bestätige u s Onboarding abschliesse

## Aamäldig

Nach dr Erstiirichtig chunsch bi jedem Zuegriff uf d Web UI uf dr Aamäldebildschirm. Mäud di mit em Passwort aa, wo du bi dr Iirichtig feschtgleit hesch.

## Passwort-Aamäldig deaktivierä

DockFlare het e Option **Passwort-Aamäldig deaktivierä** für fortgschrittni Setups, wo d Aawändig sowiso scho hinder ere externe Authentifizierigsschicht wie Cloudflare Access lauft. Für d meischte Umgebige isch das aber **nid** empfohle.

### Warum git's die Option?

Wänn du DockFlare hinder Cloudflare Access oder eme angere Authentifizierungs-Proxy betriibsch, wo SSO scho vor em Zugriff uf d Aawändig erzwunge wird, chasch d integrierti Passwort-Aamäldig abschalte, damit du di nid dopplet muesch aamälde.

### Was isch s Risiko?

Wänn die Option aktiv isch:

* sy API-Endpünkt unter Umständ ohni eigni DockFlare-Authentifizierig erreichbar
* chöi Container im glyche Docker-Netzwerk e vorglagereti Authentifizierig umgah
* verlaht sech dr Schutz komplett uf d äusseri Proxy- oder Access-Schicht

### Bispiel für e Angriffspfad

```
Internet → Cloudflare Access (Protected) → DockFlare ✅
         ↓
Docker Network → Other Container → DockFlare API (Unprotected) ❌
```

O wenn DockFlare vom Internet us guet abgesichert isch, cha e Container im glyche Docker-Netzwerk je nach Setup diräkt uf d API zuegryfe.

### Empfohlni Variante

Statt d Passwort-Aamäldig z deaktivierä, nimmsch besser eini vo dene sichere Möglichkeite:

1. **Lokali DockFlare-Aamäldig** für eifachi, integrierti Passwort-Authentifizierig
2. **OAuth/OIDC-Provider** für Single Sign-On ohni d Security-Nachteile vo ere komplett deaktivierte DockFlare-Aamäldig

Für meh Detail zu OAuth/OIDC lueg i [OAuth-Provider iirichte](OAuth-Provider-Setup.md).

### Fazit

Wänn du nid ganz genau waisch, wie dini Sicherheitsarchitektur u dini Netzwerktrennig funktioniere, söttsch d Passwort-Aamäldig aktiviert lah u für meh Komfort lieber OAuth bruuchen.
