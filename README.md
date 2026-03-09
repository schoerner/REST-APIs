## Lokale Entwicklung

Voraussetzungen: Python 3.12 / uv, Quarto

```shell
uv sync
export PYTHONPATH=$(pwd)/python/src
uv run uvicorn messageboard.main:app --host 127.0.0.1 --port 8000
```

Unterlagen generieren (Output: `quarto/_site`):
```shell
cd quarto && quarto render
```

## Docker

Das Docker-Image wird bei jedem Push auf `main` automatisch gebaut und in der
GitHub Container Registry veröffentlicht.

```shell
docker run -p 8000:8000 \
  -e PORT=8000 \
  -e DOMAIN=http://localhost:8000 \
  ghcr.io/fschmalzel/rest-apis-fortbildung:latest
```

Beim Start werden die Quarto-Unterlagen automatisch gerendert und der Server
anschließend auf Port 8000 gestartet.

### Mit Cloudflare Tunnel betreiben

Mit einem Cloudflare Tunnel lässt sich der Server über eine feste, öffentliche URL
erreichbar machen – ohne Port-Freigaben in der Schul-Firewall. Lehrer:innen können
so den Server lokal auf ihrem Gerät starten und Schüler:innen greifen über den
Browser darauf zu.

#### Voraussetzungen

- Ein Cloudflare-Konto (kostenlos unter [cloudflare.com](https://cloudflare.com))
- Eine bei Cloudflare verwaltete Domain (z. B. `meine-schule.de`)
- [Docker](https://docs.docker.com/get-docker/) und
  [Docker Compose](https://docs.docker.com/compose/install/) auf dem Rechner

#### Schritt-für-Schritt-Anleitung

**1. Tunnel im Cloudflare Zero Trust Dashboard anlegen**

1. Anmelden unter [one.dash.cloudflare.com](https://one.dash.cloudflare.com)
2. Im linken Menü: **Networks → Tunnels → Create a tunnel**
3. Connector-Typ **Cloudflared** wählen, dem Tunnel einen Namen geben
   (z. B. `rest-api-fortbildung`) und auf **Save tunnel** klicken.

**2. Tunnel-Ingress konfigurieren**

Im Abschnitt **Public Hostname** des Tunnels:

| Feld        | Wert                  |
|-------------|-----------------------|
| Subdomain   | `api` (oder beliebig) |
| Domain      | `meine-schule.de`     |
| Service URL | `http://app:8000`     |

> Wichtig: Die Service-URL muss genau `http://app:8000` lauten – `app` ist der
> interne Docker-Compose-Dienstname und ist nur im Container-Netzwerk erreichbar.

**3. Tunnel-Token kopieren**

Nach dem Speichern zeigt das Dashboard einen Token-String an (`eyJ...`).
Diesen Token für den nächsten Schritt kopieren.

**4. DNS-Eintrag**

Cloudflare legt den CNAME-Eintrag (`api.meine-schule.de → <tunnel-id>.cfargotunnel.com`)
automatisch an, sobald der Tunnel zum ersten Mal verbunden wird.

**5. Umgebungsvariablen konfigurieren**

```shell
cp .env.example .env
```

Anschließend `.env` im Texteditor öffnen und die Werte eintragen:

```dotenv
DOMAIN=https://api.meine-schule.de
PORT=8000
RESET_PASSWORD=geheimesPasswort
CLOUDFLARE_TUNNEL_TOKEN=eyJ...hier-den-kopierten-Token-einfügen...
```

> `DOMAIN` muss die vollständige öffentliche URL des Tunnels sein (mit `https://`).
> Sie wird beim Start in die Quarto-Unterlagen und die OpenAPI-Spezifikation
> eingesetzt und muss exakt mit dem im Dashboard konfigurierten Hostnamen übereinstimmen.

**6. Server starten**

```shell
docker compose up -d
```

Nach einigen Sekunden ist der Server unter `https://api.meine-schule.de` erreichbar.
Den Startfortschritt verfolgen mit:

```shell
docker compose logs -f app
```

**7. Server stoppen**

```shell
docker compose down
```

#### Hinweise

- Die Datei `.env` enthält den Tunnel-Token und darf **nicht** in ein
  Git-Repository eingecheckt werden. Sie ist bereits in `.gitignore` eingetragen.
- Beim ersten Start rendert der Container die Quarto-Unterlagen – das kann
  ein bis zwei Minuten dauern.
- Sollte der Tunnel nicht verbinden, den Token in Cloudflare widerrufen und
  einen neuen erzeugen: **Zero Trust → Networks → Tunnels → (Tunnel auswählen)
  → Configure → Token regenerieren**.

### Umgebungsvariablen

| Variable         | Standard                | Beschreibung                                                                          |
|------------------|-------------------------|---------------------------------------------------------------------------------------|
| `DOMAIN`         | `http://localhost:8000` | Vollständige URL des Servers (wird in den Unterlagen und der OpenAPI-Spec eingesetzt) |
| `PORT`           | `8000`                  | Port, auf dem der Server lauscht                                                      |
| `RESET_PASSWORD` | –                       | Passwort für den Admin-Reset-Endpunkt (siehe unten)                                   |

## Verwendung

### Datenbank zurücksetzen

Der Endpunkt `POST /api/v1/admin/reset` setzt alle Nachrichten, Nutzer und Tokens
auf die Demo-Daten zurück. Er erfordert das `RESET_PASSWORD`, das beim Start als
Umgebungsvariable gesetzt werden muss.

```shell
# Lokal
export RESET_PASSWORD=abc123
# oder Docker
docker run -p 8000:8000 -e PORT=8000 -e DOMAIN=http://localhost:8000 -e RESET_PASSWORD=abc123 ghcr.io/fschmalzel/rest-apis-fortbildung:latest
```

```shell
curl -X POST http://localhost:8000/api/v1/admin/reset \
  -H "Content-Type: application/json" \
  -d '{"password": "abc123"}'
```
