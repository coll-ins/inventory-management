"""REST routes: CRUD for inventory + helper routes for OpenFoodFacts."""
from flask import Blueprint, current_app, jsonify, request

from . import external_api
from .external_api import ExternalAPIError

bp = Blueprint("api", __name__)

STRING_FIELDS = {"name", "barcode", "brand", "category", "ingredients", "image_url"}
ALLOWED_FIELDS = STRING_FIELDS | {"quantity", "price"}


def store():
    return current_app.extensions["store"]


def error(message, status):
    return jsonify({"error": message}), status


def validate(data, partial=False):
    """Return (clean_data, errors). `partial=True` is used for PATCH."""
    if not isinstance(data, dict):
        return None, ["Request body must be a JSON object"]

    errors = []
    unknown = set(data) - ALLOWED_FIELDS
    if unknown:
        errors.append(f"Unknown field(s): {', '.join(sorted(unknown))}")

    clean = {}
    for field in STRING_FIELDS & set(data):
        if not isinstance(data[field], str):
            errors.append(f"{field} must be a string")
        else:
            clean[field] = data[field].strip()

    if "quantity" in data:
        q = data["quantity"]
        if isinstance(q, bool) or not isinstance(q, int) or q < 0:
            errors.append("quantity must be a non-negative integer")
        else:
            clean["quantity"] = q

    if "price" in data:
        p = data["price"]
        if isinstance(p, bool) or not isinstance(p, (int, float)) or p < 0:
            errors.append("price must be a non-negative number")
        else:
            clean["price"] = p

    if "name" in clean and not clean["name"]:
        errors.append("name cannot be empty")
    if not partial and "name" not in data:
        errors.append("name is required")

    if not partial:  # defaults for new items
        clean.setdefault("quantity", 0)
        clean.setdefault("price", 0.0)

    return clean, errors


@bp.get("/health")
def health():
    return jsonify({"status": "ok"})


# ---------- CRUD ----------

@bp.get("/items")
def list_items():
    items = store().all()
    name = request.args.get("name")
    category = request.args.get("category")
    if name:
        items = [i for i in items if name.lower() in i["name"].lower()]
    if category:
        items = [i for i in items if category.lower() in i.get("category", "").lower()]
    return jsonify(items)


@bp.get("/items/low-stock")
def low_stock():
    try:
        threshold = int(request.args.get("threshold", 5))
    except ValueError:
        return error("threshold must be an integer", 400)
    return jsonify([i for i in store().all() if i["quantity"] <= threshold])


@bp.get("/items/<int:item_id>")
def get_item(item_id):
    item = store().get(item_id)
    if item is None:
        return error(f"Item {item_id} not found", 404)
    return jsonify(item)


@bp.post("/items")
def create_item():
    clean, errors = validate(request.get_json(silent=True))
    if errors:
        return jsonify({"errors": errors}), 400
    if store().find_by_barcode(clean.get("barcode")):
        return error("An item with this barcode already exists", 409)
    return jsonify(store().add(clean)), 201


@bp.patch("/items/<int:item_id>")
def update_item(item_id):
    if store().get(item_id) is None:
        return error(f"Item {item_id} not found", 404)
    clean, errors = validate(request.get_json(silent=True), partial=True)
    if errors:
        return jsonify({"errors": errors}), 400
    if not clean:
        return error("No fields to update", 400)
    other = store().find_by_barcode(clean.get("barcode"))
    if other and other["id"] != item_id:
        return error("Another item already uses this barcode", 409)
    return jsonify(store().update(item_id, clean))


@bp.delete("/items/<int:item_id>")
def delete_item(item_id):
    item = store().delete(item_id)
    if item is None:
        return error(f"Item {item_id} not found", 404)
    return jsonify({"deleted": item})


# ---------- External API helpers ----------

@bp.get("/external/barcode/<barcode>")
def external_barcode(barcode):
    try:
        product = external_api.fetch_by_barcode(barcode)
    except ExternalAPIError as exc:
        return error(str(exc), 502)
    if product is None:
        return error(f"No product found for barcode {barcode}", 404)
    return jsonify(product)


@bp.get("/external/search")
def external_search():
    name = request.args.get("name", "").strip()
    if not name:
        return error("Query parameter 'name' is required", 400)
    try:
        return jsonify(external_api.search_by_name(name))
    except ExternalAPIError as exc:
        return error(str(exc), 502)


@bp.post("/items/import")
def import_item():
    """Fetch a product from OpenFoodFacts (by barcode or name) and add it to inventory."""
    body = request.get_json(silent=True)
    if not isinstance(body, dict) or not (body.get("barcode") or body.get("name")):
        return error("Provide 'barcode' or 'name' in the JSON body", 400)

    try:
        if body.get("barcode"):
            product = external_api.fetch_by_barcode(str(body["barcode"]))
        else:
            results = external_api.search_by_name(body["name"], limit=1)
            product = results[0] if results else None
    except ExternalAPIError as exc:
        return error(str(exc), 502)

    if product is None:
        return error("No matching product found on OpenFoodFacts", 404)

    # Local-only fields supplied by the employee
    extras, errors = validate(
        {k: body[k] for k in ("quantity", "price") if k in body}, partial=True
    )
    if errors:
        return jsonify({"errors": errors}), 400

    item = {"quantity": 0, "price": 0.0, **product, **extras}
    if store().find_by_barcode(item["barcode"]):
        return error("An item with this barcode already exists", 409)
    return jsonify(store().add(item)), 201
