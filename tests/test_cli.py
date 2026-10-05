"""Tests for the CLI (HTTP layer mocked)."""
from unittest.mock import MagicMock, patch

import requests

import cli

ITEM = {"id": 1, "name": "Milk", "quantity": 10, "price": 1.5, "barcode": "111", "brand": "Brookside"}


def resp(body, status=200):
    r = MagicMock()
    r.status_code = status
    r.json.return_value = body
    return r


def run_cli(argv, response):
    with patch("cli.requests.request", return_value=response) as m:
        code = cli.main(argv)
    return code, m


def test_list(capsys):
    code, m = run_cli(["list", "--name", "mi"], resp([ITEM]))
    assert code == 0
    assert "Milk" in capsys.readouterr().out
    assert m.call_args.kwargs["params"] == {"name": "mi"}


def test_list_empty(capsys):
    code, _ = run_cli(["list"], resp([]))
    assert code == 0 and "No items" in capsys.readouterr().out


def test_get_not_found(capsys):
    code, _ = run_cli(["get", "9"], resp({"error": "Item 9 not found"}, 404))
    assert code == 1 and "404" in capsys.readouterr().err


def test_add_sends_payload():
    code, m = run_cli(["add", "Milk", "--quantity", "10", "--price", "1.5"], resp(ITEM, 201))
    assert code == 0
    assert m.call_args.args[:2] == ("POST", f"{cli.BASE_URL}/items")
    assert m.call_args.kwargs["json"] == {"name": "Milk", "quantity": 10, "price": 1.5}


def test_update_only_sends_supplied_fields():
    code, m = run_cli(["update", "1", "--quantity", "3"], resp(ITEM))
    assert code == 0 and m.call_args.kwargs["json"] == {"quantity": 3}
    assert m.call_args.args[0] == "PATCH"


def test_update_without_fields_fails_locally(capsys):
    with patch("cli.requests.request") as m:
        code = cli.main(["update", "1"])
    assert code == 1 and not m.called


def test_delete(capsys):
    code, m = run_cli(["delete", "1"], resp({"deleted": ITEM}))
    assert code == 0 and m.call_args.args[0] == "DELETE"


def test_lookup_requires_exactly_one_option(capsys):
    with patch("cli.requests.request") as m:
        assert cli.main(["lookup"]) == 1
        assert cli.main(["lookup", "--barcode", "1", "--name", "x"]) == 1
    assert not m.called


def test_lookup_barcode_and_name():
    _, m = run_cli(["lookup", "--barcode", "123"], resp({"name": "X"}))
    assert m.call_args.args[1].endswith("/external/barcode/123")
    _, m = run_cli(["lookup", "--name", "nutella"], resp([]))
    assert m.call_args.kwargs["params"] == {"name": "nutella"}


def test_import_by_barcode(capsys):
    code, m = run_cli(["import", "--barcode", "123", "--quantity", "5", "--price", "2"], resp(ITEM, 201))
    assert code == 0
    assert m.call_args.kwargs["json"] == {"quantity": 5, "price": 2.0, "barcode": "123"}


def test_low_stock():
    code, m = run_cli(["low-stock", "--threshold", "3"], resp([ITEM]))
    assert code == 0 and m.call_args.kwargs["params"] == {"threshold": 3}


def test_connection_error(capsys):
    with patch("cli.requests.request", side_effect=requests.ConnectionError):
        assert cli.main(["list"]) == 2
    assert "Cannot reach API" in capsys.readouterr().err
