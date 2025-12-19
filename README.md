# URL Shortening API

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
export BASE_URL="http://localhost:5000"
python app.py
```

## Endpoints

### `POST /shorten`

```bash
curl -X POST http://localhost:5000/shorten \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
```

### `GET /<code>`

Redirects to the original URL.

### `GET /health`

Returns service health.
