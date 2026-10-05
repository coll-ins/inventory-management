"""Command-line interface for the inventory API.

Usage: python cli.py <command> [options]   (run `python cli.py -h` for help)
The API base URL defaults to http://127.0.0.1:5000 (override with INVENTORY_API_URL).
"""
import argparse
import json
import os
import sys

import requests

BASE_URL = os.environ.get("INVENTORY_API_URL", "http://127.0.0.1:5000")


def call_api(method, path, **kwargs):
    """Send a request to the API and return (status_code, parsed_json)."""
    resp = requests.request(method, f"{BASE_URL}{path}", timeout=15, **kwargs)
    try:
        body = resp.json()
    except ValueError:
        body = {}
    return resp.status_code, body


def format_item(item):
    return (
        f"[{item['id']}] {item['name']} | brand: {item.get('brand') or '-'} | "
        f"qty: {item.get('quantity', 0)} | price: {item.get('price', 0)} | "
        f"barcode: {item.get('barcode') or '-'}"
    )


def build_parser():
    p = argparse.ArgumentParser(prog="inventory", description="Inventory management CLI")
    sub = p.add_subparsers(dest="command", required=True)

    ls = sub.add_parser("list", help="List inventory items")
    ls.add_argument("--name", help="Filter by name substring")
    ls.add_argument("--category", help="Filter by category substring")

    g = sub.add_parser("get", help="Show one item")
    g.add_argument("id", type=int)

    a = sub.add_parser("add", help="Add an item manually")
    a.add_argument("name")
    a.add_argument("--quantity", type=int, default=0)
    a.add_argument("--price", type=float, default=0.0)
    a.add_argument("--barcode")
    a.add_argument("--brand")
    a.add_argument("--category")

    u = sub.add_parser("update", help="Update fields of an item")
    u.add_argument("id", type=int)
    u.add_argument("--name")
    u.add_argument("--quantity", type=int)
    u.add_argument("--price", type=float)
    u.add_argument("--barcode")
    u.add_argument("--brand")
    u.add_argument("--category")

    d = sub.add_parser("delete", help="Delete an item")
    d.add_argument("id", type=int)

    lk = sub.add_parser("lookup", help="Look up a product on OpenFoodFacts (no save)")
    lk.add_argument("--barcode")
    lk.add_argument("--name")

    im = sub.add_parser("import", help="Fetch from OpenFoodFacts and add to inventory")
    im.add_argument("--barcode")
    im.add_argument("--name")
    im.add_argument("--quantity", type=int, default=0)
    im.add_argument("--price", type=float, default=0.0)

    sub.add_parser("low-stock", help="List items at or below a stock threshold").add_argument(
        "--threshold", type=int, default=5
    )
    return p


def _fields(args, names):
    """Collect only the options the user actually supplied."""
    return {n: getattr(args, n) for n in names if getattr(args, n, None) is not None}


def run(args):
    """Execute a parsed command; return (status, body, kind)."""
    c = args.command
    if c == "list":
        params = _fields(args, ["name", "category"])
        return (*call_api("GET", "/items", params=params), "items")
    if c == "get":
        return (*call_api("GET", f"/items/{args.id}"), "item")
    if c == "add":
        payload = _fields(args, ["name", "quantity", "price", "barcode", "brand", "category"])
        return (*call_api("POST", "/items", json=payload), "item")
    if c == "update":
        payload = _fields(args, ["name", "quantity", "price", "barcode", "brand", "category"])
        if not payload:
            return 400, {"error": "Nothing to update: pass at least one option"}, "raw"
        return (*call_api("PATCH", f"/items/{args.id}", json=payload), "item")
    if c == "delete":
        return (*call_api("DELETE", f"/items/{args.id}"), "raw")
    if c == "low-stock":
        return (*call_api("GET", "/items/low-stock", params={"threshold": args.threshold}), "items")
    if c in ("lookup", "import"):
        if bool(args.barcode) == bool(args.name):
            return 400, {"error": "Provide exactly one of --barcode or --name"}, "raw"
        if c == "lookup":
            if args.barcode:
                return (*call_api("GET", f"/external/barcode/{args.barcode}"), "raw")
            return (*call_api("GET", "/external/search", params={"name": args.name}), "raw")
        payload = {"quantity": args.quantity, "price": args.price}
        payload.update(_fields(args, ["barcode", "name"]))
        return (*call_api("POST", "/items/import", json=payload), "item")
    return 400, {"error": "Unknown command"}, "raw"


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        status, body, kind = run(args)
    except requests.ConnectionError:
        print(f"Cannot reach API at {BASE_URL}. Is the server running?", file=sys.stderr)
        return 2

    if status >= 400:
        print(f"Error {status}: {json.dumps(body)}", file=sys.stderr)
        return 1
    if kind == "items":
        if not body:
            print("No items found.")
        for item in body:
            print(format_item(item))
    elif kind == "item":
        print(format_item(body))
    else:
        print(json.dumps(body, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
