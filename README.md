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
