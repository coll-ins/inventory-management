# Inventory Management System

Flask REST API + CLI for managing retail inventory. Product details can be pulled from the
[OpenFoodFacts API](https://world.openfoodfacts.org) by barcode or name and saved into inventory.

## Structure

```
app/
  __init__.py       # app factory
  routes.py         # CRUD + external API routes
  storage.py        # in-memory item list
  external_api.py   # OpenFoodFacts client
cli.py              # command-line interface (talks to the API over HTTP)
run.py              # starts the server
tests/              # pytest suite (network mocked)
```

## Installation

```bash
git clone https://github.com/coll-ins/inventory-management.git
cd inventory-management-system
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
python run.py                    # API on http://127.0.0.1:5000
python cli.py list               # in a second terminal
```

Set `INVENTORY_API_URL` if the API runs elsewhere. Data is stored in memory and resets on restart.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/items` | List items. Filters: `?name=`, `?category=` |
| GET | `/items/<id>` | Get one item |
| POST | `/items` | Create item. Body: `name` (required), `quantity`, `price`, `barcode`, `brand`, `category`, `ingredients`, `image_url` |
| PATCH | `/items/<id>` | Update any subset of fields |
| DELETE | `/items/<id>` | Delete item |
| GET | `/items/low-stock?threshold=5` | Items with quantity <= threshold |
| GET | `/external/barcode/<barcode>` | Look up product on OpenFoodFacts (not saved) |
| GET | `/external/search?name=<text>` | Search OpenFoodFacts by name (not saved) |
| POST | `/items/import` | Fetch by `barcode` or `name` and add to inventory. Optional `quantity`, `price` |

Status codes: `200/201` success, `400` validation error, `404` not found, `409` duplicate barcode,
`502` OpenFoodFacts unreachable.

Example:

```bash
curl -X POST localhost:5000/items -H "Content-Type: application/json" \
  -d '{"name": "Milk", "quantity": 10, "price": 1.5}'
curl -X PATCH localhost:5000/items/1 -H "Content-Type: application/json" -d '{"quantity": 8}'
curl -X POST localhost:5000/items/import -H "Content-Type: application/json" \
  -d '{"barcode": "3017620422003", "quantity": 20, "price": 6.99}'
```

## CLI Usage

```bash
python cli.py add "Milk" --quantity 10 --price 1.5 --brand Brookside
python cli.py list
python cli.py list --name milk
python cli.py get 1
python cli.py update 1 --quantity 8 --price 1.6
python cli.py delete 1
python cli.py low-stock --threshold 5
python cli.py lookup --barcode 3017620422003     # view only
python cli.py lookup --name nutella              # view only
python cli.py import --barcode 3017620422003 --quantity 20 --price 6.99
python cli.py import --name "nutella" --quantity 5
```

Exit codes: `0` ok, `1` API/validation error, `2` API not reachable.

## Tests

```bash
pytest -v
```

Covers CRUD routes, validation, OpenFoodFacts client and import routes (mocked, no network), and CLI commands.
