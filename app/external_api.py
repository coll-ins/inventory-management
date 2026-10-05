"""Thin client for the OpenFoodFacts API (https://world.openfoodfacts.org)."""
import requests

BASE_URL = "https://world.openfoodfacts.org"
HEADERS = {"User-Agent": "InventoryManagementSystem/1.0 (student-project)"}
TIMEOUT = 10
FIELDS = "code,product_name,generic_name,brands,categories,ingredients_text,image_url"


class ExternalAPIError(Exception):
    """Raised when OpenFoodFacts is unreachable or returns bad data."""


def _normalize(product):
    """Map an OpenFoodFacts product to our inventory field names."""
    return {
        "name": product.get("product_name") or product.get("generic_name") or "Unknown product",
        "barcode": str(product.get("code", "")),
        "brand": (product.get("brands") or "").split(",")[0].strip(),
        "category": (product.get("categories") or "").split(",")[0].strip(),
        "ingredients": product.get("ingredients_text") or "",
        "image_url": product.get("image_url") or "",
    }


def fetch_by_barcode(barcode):
    """Return a normalized product dict, or None if the barcode is unknown."""
    try:
        resp = requests.get(
            f"{BASE_URL}/api/v2/product/{barcode}.json",
            params={"fields": FIELDS},
            headers=HEADERS,
            timeout=TIMEOUT,
        )
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        data = resp.json()
    except (requests.RequestException, ValueError) as exc:
        raise ExternalAPIError(f"OpenFoodFacts request failed: {exc}") from exc

    if data.get("status") != 1 or not data.get("product"):
        return None
    product = data["product"]
    product.setdefault("code", barcode)
    return _normalize(product)


def search_by_name(name, limit=5):
    """Return a list of normalized products matching `name` (may be empty)."""
    try:
        resp = requests.get(
            f"{BASE_URL}/cgi/search.pl",
            params={
                "search_terms": name,
                "search_simple": 1,
                "action": "process",
                "json": 1,
                "page_size": limit,
                "fields": FIELDS,
            },
            headers=HEADERS,
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
    except (requests.RequestException, ValueError) as exc:
        raise ExternalAPIError(f"OpenFoodFacts request failed: {exc}") from exc

    products = [p for p in data.get("products", []) if p.get("product_name")]
    return [_normalize(p) for p in products[:limit]]
