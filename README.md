# Inventory Management System

An administrator tool for a small retail company to manage stock. It has three parts:

1. **A Flask REST API** for adding, viewing, editing and deleting inventory items.
2. **An OpenFoodFacts integration** that fetches real product data (name, brand, category, ingredients, image) by barcode or name and can save it straight into inventory.
3. **A command-line interface (CLI)** so employees can do all of the above from a terminal without writing HTTP requests.

A pytest suite (38 tests) covers the API, the external API client and the CLI.

---

## Table of Contents

- [How it works](#how-it-works)
- [Project structure](#project-structure)
- [Installation](#installation)
- [Running the project](#running-the-project)
- [The inventory item](#the-inventory-item)
- [API reference](#api-reference)
- [CLI reference](#cli-reference)
- [External API integration](#external-api-integration)
- [Testing](#testing)
- [Design decisions and limitations](#design-decisions-and-limitations)
- [Troubleshooting](#troubleshooting)
- [Git workflow used](#git-workflow-used)

---

## How it works

```
 Employee
    |
    |  python cli.py ...                curl / browser
    v                                        |
 +---------+      HTTP (requests)            v
 | cli.py  | ------------------------> +-------------+
 +---------+                           | Flask API   |  app/routes.py
                                       +------+------+
                                              |
                        +---------------------+--------------------+
                        v                                          v
                 +-------------+                         +------------------+
                 | storage.py  |                         | external_api.py  |
                 | (in-memory  |                         | OpenFoodFacts    |
                 |  item list) |                         | client           |
                 +-------------+                         +------------------+
```

- The **CLI never touches data directly**. It sends HTTP requests to the API, so the API stays the single source of truth.
- The **routes** validate input, then call the **storage** layer (local items) or the **external API client** (OpenFoodFacts).
- **Import** combines both: fetch a product from OpenFoodFacts, add the stock quantity and price the employee supplies, and save it.

---

## Project structure

```
inventory-management/
├── app/
│   ├── __init__.py        # App factory: creates Flask app, store, JSON error handlers
│   ├── routes.py          # All endpoints + input validation
│   ├── storage.py         # InventoryStore: in-memory list of items with CRUD methods
│   └── external_api.py    # OpenFoodFacts client (barcode lookup, name search)
├── tests/
│   ├── conftest.py        # Shared fixtures: fresh test client per test, sample item
│   ├── test_crud.py       # 14 tests: CRUD routes, validation, filters, error responses
│   ├── test_external_api.py  # 12 tests: OpenFoodFacts client + external/import routes (mocked)
│   └── test_cli.py        # 12 tests: every CLI command (HTTP mocked)
├── cli.py                 # Command-line interface (argparse)
├── run.py                 # Starts the development server
├── requirements.txt       # Flask, requests, pytest
├── pytest.ini             # Test configuration
├── .gitignore             # Ignores .venv, caches, .env
└── README.md
```

| File | Responsibility |
|------|----------------|
| `app/__init__.py` | `create_app()` builds a fresh app with its own store. Tests use this so they never share data. Also returns JSON (not HTML) for 404 and 405 errors. |
| `app/routes.py` | One blueprint with every endpoint. `validate()` checks types, rejects unknown fields and applies defaults. |
| `app/storage.py` | A plain Python list plus an ID counter. IDs are never reused after deletion. |
| `app/external_api.py` | Calls OpenFoodFacts, maps its fields to ours, and converts network failures into a single `ExternalAPIError`. |
| `cli.py` | Parses commands, calls the API, prints readable output, returns exit codes. |

---

## Installation

Requires Python 3.9+.

```bash
git clone https://github.com/coll-ins/inventory-management.git
cd inventory-management
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

---

## Running the project

Use two terminals, both inside the project folder with the virtual environment activated.

**Terminal 1: start the API**
```bash
python run.py
```
The API runs at `http://127.0.0.1:5000`.

**Terminal 2: use the CLI**
```bash
python cli.py list
```

If the API runs on a different address, set `INVENTORY_API_URL`:
```bash
export INVENTORY_API_URL=http://192.168.1.10:5000
```

> Data is stored in memory. Stopping the server clears all items.

---

## The inventory item

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `id` | integer | auto | Assigned by the server, never reused |
| `name` | string | **yes** | Cannot be empty |
| `quantity` | integer | no | Default `0`. Must be `>= 0` |
| `price` | number | no | Default `0.0`. Must be `>= 0` |
| `barcode` | string | no | Must be unique across items |
| `brand` | string | no | |
| `category` | string | no | |
| `ingredients` | string | no | Filled automatically on import |
| `image_url` | string | no | Filled automatically on import |

Validation rules: unknown fields are rejected, booleans are not accepted as numbers, and strings are trimmed.

---

## API reference

Base URL: `http://127.0.0.1:5000`. All responses are JSON.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/items` | List items. Optional filters: `?name=` and `?category=` (case-insensitive substring) |
| GET | `/items/<id>` | Get one item |
| POST | `/items` | Create an item |
| PATCH | `/items/<id>` | Update any subset of fields |
| DELETE | `/items/<id>` | Delete an item |
| GET | `/items/low-stock` | Items with `quantity <= threshold` (`?threshold=5` by default) |
| GET | `/external/barcode/<barcode>` | Look up a product on OpenFoodFacts (not saved) |
| GET | `/external/search?name=<text>` | Search OpenFoodFacts by name, up to 5 results (not saved) |
| POST | `/items/import` | Fetch from OpenFoodFacts by `barcode` or `name` and save to inventory |

### Status codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Item created |
| 400 | Validation error or missing parameter |
| 404 | Item or product not found |
| 405 | Method not allowed |
| 409 | Duplicate barcode |
| 502 | OpenFoodFacts unreachable or returned bad data |

### Examples

**Create**
```bash
curl -X POST localhost:5000/items -H "Content-Type: application/json" \
  -d '{"name": "Milk", "quantity": 10, "price": 1.5}'
```
```json
{"id": 1, "name": "Milk", "quantity": 10, "price": 1.5}
```

**Update (partial)**
```bash
curl -X PATCH localhost:5000/items/1 -H "Content-Type: application/json" -d '{"quantity": 8}'
```

**Delete**
```bash
curl -X DELETE localhost:5000/items/1
```

**Import from OpenFoodFacts**
```bash
curl -X POST localhost:5000/items/import -H "Content-Type: application/json" \
  -d '{"barcode": "3017620422003", "quantity": 20, "price": 6.99}'
```

**Validation error**
```json
{"errors": ["quantity must be a non-negative integer"]}
```

---

## CLI reference

```bash
python cli.py -h                  # list all commands
```

| Command | Description |
|---------|-------------|
| `list [--name X] [--category X]` | List items, optionally filtered |
| `get <id>` | Show one item |
| `add <name> [--quantity N] [--price P] [--barcode B] [--brand X] [--category X]` | Add an item |
| `update <id> [--name X] [--quantity N] [--price P] [--barcode B] [--brand X] [--category X]` | Change only the fields you pass |
| `delete <id>` | Delete an item |
| `low-stock [--threshold N]` | Items at or below the threshold (default 5) |
| `lookup --barcode B` or `lookup --name X` | View OpenFoodFacts data without saving |
| `import --barcode B` or `import --name X [--quantity N] [--price P]` | Fetch from OpenFoodFacts and save to inventory |

### Examples

```bash
python cli.py add "Milk" --quantity 10 --price 1.5 --brand Brookside
python cli.py list
python cli.py list --name milk
python cli.py update 1 --quantity 8 --price 1.6
python cli.py low-stock --threshold 5
python cli.py lookup --barcode 3017620422003
python cli.py import --barcode 3017620422003 --quantity 20 --price 6.99
python cli.py import --name "oreo" --quantity 10 --price 2
python cli.py delete 1
```

Sample output:
```
[1] Milk | brand: Brookside | qty: 10 | price: 1.5 | barcode: -
```

### Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | API or validation error (message printed to stderr) |
| 2 | API server not reachable |

---

## External API integration

Product data comes from the free [OpenFoodFacts API](https://world.openfoodfacts.org).

- **By barcode:** `GET /api/v2/product/<barcode>.json` returns one exact product, or none.
- **By name:** `GET /cgi/search.pl` returns the best matches. `lookup --name` shows up to 5. `import --name` saves only the top result.

OpenFoodFacts fields are mapped to inventory fields:

| OpenFoodFacts | Inventory |
|---------------|-----------|
| `product_name` (or `generic_name`) | `name` |
| `code` | `barcode` |
| `brands` (first value) | `brand` |
| `categories` (first value) | `category` |
| `ingredients_text` | `ingredients` |
| `image_url` | `image_url` |

Quantity and price are not available from OpenFoodFacts, so the employee supplies them on import (default `0`).

Requests have a 10-second timeout and send a User-Agent header, as OpenFoodFacts requires. Network errors, timeouts and malformed responses become a `502` from the API and are never raised as uncaught exceptions.

---

## Testing

```bash
pytest -v
```

38 tests, no network required (all external calls are mocked):

| File | Tests | What it covers |
|------|-------|----------------|
| `tests/test_crud.py` | 14 | Create, read, filter, patch, delete, defaults, validation errors, duplicate barcodes, low-stock, JSON 404/405 |
| `tests/test_external_api.py` | 12 | Barcode lookup, name search, not found, network errors, bad JSON, external routes, import success/duplicate/missing/invalid/failure |
| `tests/test_cli.py` | 12 | Every command, payload correctness, local validation, API errors, connection failure |

Each test gets a fresh app, so tests cannot affect each other.

To check the live integration manually, run the server and use `python cli.py lookup --barcode 3017620422003`.

---

## Design decisions and limitations

- **In-memory storage.** Items are kept in a Python list, as the brief describes ("database array"). Data resets when the server restarts. Swapping `storage.py` for SQLite or PostgreSQL would not require changes to the routes.
- **Barcode is unique, name is not.** Two items named "Milk" are allowed if they have no barcode or different barcodes.
- **PATCH instead of PUT.** Updates change only the supplied fields.
- **CLI talks to the API over HTTP** rather than importing the storage layer, so both interfaces behave identically.
- **No authentication.** This is an internal admin tool for the assignment. A real deployment would need login, roles and HTTPS.
- **Development server only.** `run.py` uses Flask's debug server. Production would use gunicorn or similar, with debug mode off.
- **OpenFoodFacts covers food and drink products.** Non-food items must be added manually. Product data is crowd-sourced and can contain typos or missing fields.

Possible future improvements: persistent database, pagination, authentication, CSV export, stock-change history.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `Cannot reach API at http://127.0.0.1:5000` | Start the server with `python run.py` in another terminal |
| `Error 502` on lookup/import | OpenFoodFacts is slow or down. Check your internet connection and retry |
| `Error 404: No product found` | Barcode is not in OpenFoodFacts. Try `lookup --name` or add the item manually |
| `Error 409` on import | An item with that barcode is already in inventory |
| `No files were found in testpaths` | You are in the wrong folder or on a branch without `tests/`. Run from the project root |
| `Address already in use` | Another server is running on port 5000. Stop it or kill the old process |

---

## Git workflow used

Each feature was developed on its own branch, pushed, merged through a pull request, and the branch deleted.

| PR | Branch | Contents |
|----|--------|----------|
| #1 | `feature/flask-api` | Flask CRUD API, OpenFoodFacts integration, API tests |
| #2 | `feature/cli` | CLI and CLI tests |
| #3 | `docs/readme` | README |
