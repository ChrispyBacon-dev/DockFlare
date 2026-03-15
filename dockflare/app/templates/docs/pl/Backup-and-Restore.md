# Kopia zapasowa i przywracanie

DockFlare 3.0 wprowadza pełne archiwum kopii zapasowej, dzięki czemu możesz przenieść Mastera na nowy sprzęt, odtworzyć go po awarii lub przygotować aktualizację bez ręcznego grzebania w katalogu danych.

## Co zostanie zapisane
- `dockflare.key` – klucz Fernet, który odblokowuje każdy zaszyfrowany plik.
- `dockflare_config.dat` – zaszyfrowane poświadczenia Cloudflare, konto panelu administracyjnego i ustawienia środowiska wykonawczego.
- `agent_keys.dat` – zaszyfrowane klucze API agenta i metadane audytu.
- `state.json` – zwykła kopia lustrzana JSON reguł, agentów i grup dostępu.
- `manifest.json` – sumy kontrolne i informacje o wersji archiwum (generowane automatycznie).

Wszystkie te pliki są zebrane w jeden `dockflare_backup_YYYYMMDD_HHMMSS.zip`. Zachowaj ZIP i wyodrębnione pliki razem; bez `dockflare.key` zaszyfrowane artefakty są bezużyteczne.

## Tworzenie kopii zapasowej
1. Otwórz **Ustawienia → Kopia zapasowa i przywracanie** w panelu administracyjnym.
2. Kliknij **Pobierz kopię zapasową (.zip)**.
3. Przechowuj archiwum w bezpiecznym miejscu. Traktuj to jak dane uwierzytelniające — zawiera wszystko, co potrzebne do kontrolowania konta Cloudflare za pośrednictwem DockFlare.

Kopie zapasowe można wykonywać, gdy Master jest uruchomiony. Każde archiwum zawiera manifest ze skrótami SHA-256, więc łatwo wykryć uszkodzone pobranie.

## Przywracanie na istniejącym Masterze
1. Przejdź do **Ustawienia → Kopia zapasowa i przywracanie**.
2. Prześlij `.zip` poprzez **Przywróć z kopii zapasowej**.
3. Potwierdź ostrzeżenie: przywracanie powoduje nadpisanie konfiguracji, kluczy agentów i reguł.

DockFlare odtwarza zaszyfrowane pliki, ponownie ładuje `state.json` i, jeśli to konieczne, zapisuje flagę ponownego uruchomienia. Kontener zakończy pracę kilka sekund później, aby Docker mógł uruchomić go ponownie z nową konfiguracją. Panel administracyjny będzie ponownie dostępny z przywróconymi poświadczeniami.

Starsze pliki `state.json` są nadal akceptowane w przypadku częściowego przywracania. Przesłanie czystego pliku JSON zastępuje jedynie reguły i pomija zaszyfrowaną konfigurację.

## Przywracanie podczas pracy kreatora instalacji
W świeżej instalacji zobaczysz łącze **Przywróć z kopii zapasowej** przed krokiem 1 kreatora Pre-Flight.

1. Prześlij archiwum ZIP z kopią zapasową.
2. DockFlare zapisuje zaszyfrowane artefakty i stan na dysk.
3. Kontener uruchamia się automatycznie; kiedy wróci, zaloguj się na przywrócone konto administratora.

Ten przepływ jest najszybszym sposobem na sklonowanie produkcyjnego Mastera lub odtworzenie instancji po wyczyszczeniu woluminu danych. Nie musisz ponownie uruchamiać kreatora ani ponownie wprowadzać poświadczeń Cloudflare.

## Po przywróceniu
- Odwiedź **Ustawienia → Kopia zapasowa i przywracanie**, aby potwierdzić najnowszy znacznik czasu manifestu.
- Sprawdź **Agenci → Przegląd**, aby upewnić się, że zarejestrowani agenci ponownie się połączyli. Wydaj ponownie klucze agentów, jeśli je rotowałeś.
- Wywołaj uzgadnianie, jeśli przywróciłeś dane do innego środowiska (`Actions → Reconcile Now`).

Regularnie twórz kopie zapasowe offline i łącz je z kontrolą wersji plików konfiguracyjnych, aby móc szybko odbudować całe wdrożenie.
