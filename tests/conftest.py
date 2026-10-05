import pytest

from app import create_app


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


@pytest.fixture
def sample(client):
    """Create one item and return its JSON."""
    r = client.post("/items", json={"name": "Milk", "quantity": 10, "price": 1.5, "barcode": "111"})
    return r.get_json()
