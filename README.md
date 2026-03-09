## Installation

Folgendes muss installiert sein:
* Python 3.12 oder uv
* quarto
* LaTeX (LuaTeX und extra fonts)

## Unterlagen

Mit quarto wird die Webseite und die .pdfs generiert.
```shell
cd quarto && quarto render
```

Alle Unterlagen sind dann in quarto/_site

## MessageBoard starten

Pakete installieren
```shell
pip install .
# oder
uv sync
```


Den Host und den Port muss man entsprechend anpassen.
RESET_PASSWORD ist für das zurücksetzen der Datenbank.
```shell
export PYTHONPATH=$(pwd)/python/src
export RESET_PASSWORD=abc123


uvicorn messageboard.main:app --host 127.0.0.1 --port 8000
# oder mit uv
uv run uvicorn messageboard.main:app --host 127.0.0.1 --port 8000
```

## Docker

Das Docker-Image wird bei jedem Push auf `main` automatisch gebaut und in der
GitHub Container Registry veröffentlicht.

Image ziehen:
```shell
docker pull ghcr.io/fschmalzel/rest-apis-fortbildung:latest
```

Container starten:
```shell
docker run -p 8000:8000 \
  -e DOMAIN=http://localhost:8000 \
  ghcr.io/fschmalzel/rest-apis-fortbildung:latest
```

Beim Start werden die Quarto-Unterlagen automatisch gerendert und der Server
anschließend auf Port 8000 gestartet.

### Umgebungsvariablen

| Variable | Standard                | Beschreibung                                                                            |
|----------|-------------------------|-----------------------------------------------------------------------------------------|
| `DOMAIN` | `http://localhost:8000` | Vollständige URL des Servers (wird in den Unterlagen und der OpenAPI-Spec eingesetzt)   |
| `PORT`   | `8000`                  | Port, auf dem der Server lauscht                                                        |