"""Tests for the OpenFoodFacts client and the routes that use it (all network mocked)."""
from unittest.mock import MagicMock, patch

import pytest
import requests

from app import external_api
from app.external_api import ExternalAPIError

PRODUCT = {
    "name": "Nutella",
    "barcode": "3017620422003",
    "brand": "Ferrero",
    "category": "Spreads",
    "ingredients": "Sugar, palm oil",
    "image_url": "http://img",
}


def fake_response(json_data, status=200):
    r = MagicMock()
    r.status_code = status
    r.json.return_value = json_data
    if status >= 400 and status != 404:
        r.raise_for_status.side_effect = requests.HTTPError("boom")
    return r


# ---- client ----

def test_fetch_by_barcode_success():
    payload = {"status": 1, "product": {"code": "3017620422003", "product_name": "Nutella",
               "brands": "Ferrero,Other", "categories": "Spreads,Sweet"}}
    with patch("app.external_api.requests.get", return_value=fake_response(payload)):
        p = external_api.fetch_by_barcode("3017620422003")
    assert p["name"] == "Nutella" and p["brand"] == "Ferrero" and p["category"] == "Spreads"


def test_fetch_by_barcode_not_found():
    with patch("app.external_api.requests.get", return_value=fake_response({"status": 0})):
        assert external_api.fetch_by_barcode("000") is None
    with patch("app.external_api.requests.get", return_value=fake_response({}, 404)):
        assert external_api.fetch_by_barcode("000") is None


def test_fetch_by_barcode_network_error():
    with patch("app.external_api.requests.get", side_effect=requests.ConnectionError("down")):
        with pytest.raises(ExternalAPIError):
            external_api.fetch_by_barcode("123")


def test_search_by_name_filters_nameless_products():
    payload = {"products": [{"code": "1", "product_name": "A"}, {"code": "2"}]}
    with patch("app.external_api.requests.get", return_value=fake_response(payload)):
        results = external_api.search_by_name("a")
    assert [r["name"] for r in results] == ["A"]


def test_search_bad_json_raises():
    resp = fake_response({})
    resp.json.side_effect = ValueError("bad")
    with patch("app.external_api.requests.get", return_value=resp):
        with pytest.raises(ExternalAPIError):
            external_api.search_by_name("x")


# ---- routes ----

def test_external_barcode_route(client):
    with patch("app.external_api.fetch_by_barcode", return_value=PRODUCT):
        assert client.get("/external/barcode/3017620422003").get_json()["brand"] == "Ferrero"
    with patch("app.external_api.fetch_by_barcode", return_value=None):
        assert client.get("/external/barcode/0").status_code == 404
    with patch("app.external_api.fetch_by_barcode", side_effect=ExternalAPIError("x")):
        assert client.get("/external/barcode/0").status_code == 502


def test_external_search_route(client):
    assert client.get("/external/search").status_code == 400
    with patch("app.external_api.search_by_name", return_value=[PRODUCT]):
        assert len(client.get("/external/search?name=nutella").get_json()) == 1
    with patch("app.external_api.search_by_name", side_effect=ExternalAPIError("x")):
        assert client.get("/external/search?name=x").status_code == 502


def test_import_by_barcode_adds_to_inventory(client):
    with patch("app.external_api.fetch_by_barcode", return_value=PRODUCT):
        r = client.post("/items/import", json={"barcode": "3017620422003", "quantity": 7, "price": 4.5})
    body = r.get_json()
    assert r.status_code == 201
    assert body["name"] == "Nutella" and body["quantity"] == 7 and body["price"] == 4.5
    assert len(client.get("/items").get_json()) == 1


def test_import_by_name(client):
    with patch("app.external_api.search_by_name", return_value=[PRODUCT]):
        assert client.post("/items/import", json={"name": "nutella"}).status_code == 201


def test_import_duplicate_and_missing(client):
    with patch("app.external_api.fetch_by_barcode", return_value=PRODUCT):
        client.post("/items/import", json={"barcode": "3017620422003"})
        assert client.post("/items/import", json={"barcode": "3017620422003"}).status_code == 409
    with patch("app.external_api.fetch_by_barcode", return_value=None):
        assert client.post("/items/import", json={"barcode": "0"}).status_code == 404
    assert client.post("/items/import", json={}).status_code == 400


def test_import_bad_quantity(client):
    with patch("app.external_api.fetch_by_barcode", return_value=PRODUCT):
        r = client.post("/items/import", json={"barcode": "1", "quantity": -5})
    assert r.status_code == 400


def test_import_api_failure(client):
    with patch("app.external_api.fetch_by_barcode", side_effect=ExternalAPIError("down")):
        assert client.post("/items/import", json={"barcode": "1"}).status_code == 502
