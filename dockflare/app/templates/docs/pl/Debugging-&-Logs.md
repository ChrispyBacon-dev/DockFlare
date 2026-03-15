# Debugowanie i dzienniki

Podczas rozwiązywania problemów z DockFlare głównymi narzędziami są dzienniki generowane przez kontener DockFlare i zarządzanego przez niego agenta `cloudflared`.

## 1. Sprawdzanie dzienników kontenera DockFlare

Najważniejszym źródłem informacji są dane wyjściowe dziennika z samego kontenera DockFlare. Dzienniki te zapewniają szczegółowy widok w czasie rzeczywistym tego, co robi DockFlare.

### Co znajdziesz w logach:
* Wykrywanie zdarzeń uruchamiania/zatrzymywania kontenera Docker.
* Przetwarzanie etykiet `dockflare.*`.
* Wykonywane są połączenia z interfejsem API Cloudflare.
* Komunikaty o powodzeniu lub szczegółowe odpowiedzi na błędy z interfejsu API Cloudflare.
* Stan zadań w tle, takich jak czyszczenie zasobów.

### Jak wyświetlić dzienniki:
Aby wyświetlić logi, użyj następującego polecenia Docker w terminalu:
```bash
# View the full log history
docker logs dockflare

# Follow the logs in real-time
docker logs -f dockflare
```

## 2. Korzystanie z dzienników czasu rzeczywistego w panelu administracyjnym

Dla wygody panel DockFlare zawiera **przeglądarkę logów w czasie rzeczywistym** u dołu strony głównej.

Ta przeglądarka przesyła strumieniowo dokładnie te same dzienniki, które zobaczysz w przypadku `docker logs -f dockflare`, ale zapewnia łatwy sposób sprawdzenia, co dzieje się teraz, bez opuszczania przeglądarki. Jest to szczególnie przydatne do obserwowania działań podejmowanych przez DockFlare natychmiast po uruchomieniu lub zatrzymaniu kontenera.

## 3. Sprawdzanie dzienników agenta `cloudflared`

Jeśli podejrzewasz, że problem dotyczy połączenia między Twoim serwerem a siecią Cloudflare, możesz bezpośrednio sprawdzić dzienniki kontenera agenta `cloudflared`.

### Jak wyświetlić dzienniki agenta:
Najpierw musisz znaleźć nazwę kontenera agenta. Domyślnie nosi on nazwę `cloudflared-agent-<tunnel-name>`, gdzie `<tunnel-name>` to nazwa tunelu skonfigurowanego w ustawieniach DockFlare.

Dokładną nazwę można znaleźć za pomocą `docker ps`.

Gdy już masz nazwę, uruchom:
```bash
# Replace with the actual container name
docker logs cloudflared-agent-dockflare-tunnel
```

Te dzienniki są przydatne do diagnozowania:
* Błędy połączenia z krawędzią Cloudflare.
* Problemy z uwierzytelnianiem za pomocą tokena tunelu.
* Błędy na poziomie protokołu dla ruchu przesyłanego przez serwer proxy.

**Uwaga:** Dotyczy to tylko sytuacji, gdy używasz domyślnego **Trybu wewnętrznego**. Jeśli używasz [Trybu zewnętrznego](External-cloudflared-Mode.md), musisz sprawdzić dzienniki własnego procesu agenta `cloudflared`.

## 4. Sprawdzanie pulpitu nawigacyjnego Cloudflare

Na koniec nie zapomnij użyć panelu Cloudflare jako narzędzia do debugowania.
* **Strona DNS:** Sprawdź, czy rekordy CNAME zostały utworzone zgodnie z oczekiwaniami.
* **Panel Zero Trust:** Przejdź do **Access -> Tunnels**, aby sprawdzić stan tunelu i reguły ingress.
* **Panel Zero Trust:** Przejdź do **Access -> Applications**, aby sprawdzić konfigurację i stan zasad Zero Trust. Pole „Last Seen” w zasadach bywa bardzo pomocne.
