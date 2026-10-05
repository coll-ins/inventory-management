"""Tests for CRUD routes."""


def test_health(client):
    assert client.get("/health").get_json() == {"status": "ok"}


def test_create_item_applies_defaults(client):
    r = client.post("/items", json={"name": "Bread"})
    assert r.status_code == 201
    body = r.get_json()
    assert body["id"] == 1 and body["quantity"] == 0 and body["price"] == 0.0


def test_create_requires_name(client):
    r = client.post("/items", json={"quantity": 3})
    assert r.status_code == 400
    assert "name is required" in r.get_json()["errors"]


def test_create_rejects_bad_types(client):
    r = client.post("/items", json={"name": "X", "quantity": -1, "price": "free"})
    assert r.status_code == 400
    assert len(r.get_json()["errors"]) == 2


def test_create_rejects_unknown_field_and_non_json(client):
    assert client.post("/items", json={"name": "X", "color": "red"}).status_code == 400
    assert client.post("/items", data="not json").status_code == 400


def test_duplicate_barcode_conflict(client, sample):
    r = client.post("/items", json={"name": "Other", "barcode": "111"})
    assert r.status_code == 409


def test_list_and_filter(client, sample):
    client.post("/items", json={"name": "Orange Juice", "category": "Drinks"})
    assert len(client.get("/items").get_json()) == 2
    assert len(client.get("/items?name=milk").get_json()) == 1
    assert len(client.get("/items?category=drinks").get_json()) == 1


def test_get_item_and_404(client, sample):
    assert client.get(f"/items/{sample['id']}").get_json()["name"] == "Milk"
    assert client.get("/items/999").status_code == 404


def test_patch_updates_only_given_fields(client, sample):
    r = client.patch(f"/items/{sample['id']}", json={"quantity": 4})
    body = r.get_json()
    assert r.status_code == 200
    assert body["quantity"] == 4 and body["name"] == "Milk"


def test_patch_errors(client, sample):
    assert client.patch("/items/999", json={"quantity": 1}).status_code == 404
    assert client.patch(f"/items/{sample['id']}", json={}).status_code == 400
    assert client.patch(f"/items/{sample['id']}", json={"price": -2}).status_code == 400


def test_patch_barcode_conflict(client, sample):
    other = client.post("/items", json={"name": "Eggs", "barcode": "222"}).get_json()
    r = client.patch(f"/items/{other['id']}", json={"barcode": "111"})
    assert r.status_code == 409


def test_delete(client, sample):
    r = client.delete(f"/items/{sample['id']}")
    assert r.status_code == 200
    assert client.get(f"/items/{sample['id']}").status_code == 404
    assert client.delete(f"/items/{sample['id']}").status_code == 404


def test_low_stock(client, sample):
    client.post("/items", json={"name": "Salt", "quantity": 2})
    names = [i["name"] for i in client.get("/items/low-stock?threshold=5").get_json()]
    assert names == ["Salt"]
    assert client.get("/items/low-stock?threshold=abc").status_code == 400


def test_unknown_route_and_method_return_json(client):
    assert client.get("/nope").get_json()["error"]
    assert client.put("/items").status_code == 405
