# DNS-Zone verwalte

DockFlare cha DNS-Iiträg über mehri Domains, also mehri Cloudflare-Zone im gliiche Account, verwalte. So chasch du Dienscht uf `service-a.domain-one.com` u `service-b.another-domain.org` mit dr glyche DockFlare-Instanz fahre.

## Standard-Zone

Bi dr erschte Iirichtig gisch du e **Zone ID** aa. Das isch d **Standard-Zone**, wo DockFlare standardmässig alli DNS-Iiträg drin aaleit. Wänn du nume e einzigi Domain hesch, längt das völlig.

## D Zone pro Dienst überschrybe

Wänn e Dienst i nere andere Domain söll aagleit wärde als i dr Standard-Zone, chasch s Label `dockflare.zonename` bruuche.

Mit däm Label seitsch DockFlare explizit, i wellere Zone dr DNS-Iitrag für genau dä Dienst söll erstellt wärde.

### Was wichtig isch

Damit das funktioniert, mues dis **Cloudflare API-Token** für **alli** Zone, wo du wotsch bruuche, d Berechtigung `Zone:DNS:Edit` ha.

### Bispil

Näh mer aa, dini Standard-Zone isch `example.com`, aber du wotsch e neue Dienst uf `media.io` veröffentliche.

```yaml
services:
  # This service will be created in the default zone (example.com)
  service-one:
    image: nginx
    labels:
      - "dockflare.enable=true"
      - "dockflare.hostname=nginx.example.com"
      - "dockflare.service=http://service-one:80"

  # This service will be created in the 'media.io' zone
  service-two:
    image: portainer/portainer-ce
    labels:
      - "dockflare.enable=true"
      - "dockflare.hostname=portainer.media.io"
      - "dockflare.service=http://service-two:9000"
      # Override the default zone for this service
      - "dockflare.zonename=media.io"
```

Wänn du das deploysch, macht DockFlare Folgends:
1. E CNAME-Iitrag für `nginx.example.com` i dr Zone `example.com`
2. E CNAME-Iitrag für `portainer.media.io` i dr Zone `media.io`

Beidi Hostname wärde als Ingress-Regle am glyche Cloudflare-Tunnel zuegordnet.

## DNS-Iiträg i dr Web UI aluege

Uf dr **Settings**-Syte zeigt DockFlare alli Cloudflare-Tunnel i dim Account mitsamt de CNAME-Iiträg, wo druf verwise.

Wänn i däre Aazeig zusätzlich no meh Zone söue usgläse wärde, setz d Umgebigsvariable `TUNNEL_DNS_SCAN_ZONE_NAMES`.

### `TUNNEL_DNS_SCAN_ZONE_NAMES`

Die Variable erwartet e kommagtrennti Liste vo Zonename, wo d UI zusätzlich zur Standard-Zone nach Tunnel-DNS-Iiträg söll dürchsueche.

**Beispiel `docker-compose.yml`:**
```yaml
services:
  dockflare:
    image: alplat/dockflare:stable
    # ... other settings
    environment:
      # Tell the UI to scan these zones in addition to the default one
      - TUNNEL_DNS_SCAN_ZONE_NAMES=media.io,another-domain.org
```

So hesch du i dr Tunnel-Übersicht e vollständigere Sicht uf alli relevante DNS-Iiträg über mehri Zone.
