import pytest
from fastapi.testclient import TestClient

from app import api
from cargar_csv import load_fixture

client = TestClient(api.app)


@pytest.fixture(autouse=True)
def datos_limpios():
    """Antes de cada prueba se recargan los pedidos, así son independientes."""
    api.orders.clear()
    api.orders.update(load_fixture())


def test_get_order_200():
    r = client.get("/orders/O001")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "DRAFT"
    assert body["units"] == 4
    assert body["total"] == "2100.00"
    assert body["discount_rate"] == "0.10"


def test_get_order_404():
    assert client.get("/orders/O_INEXISTENTE").status_code == 404


def test_confirm_inexistente_404():
    assert client.post("/orders/O_INEXISTENTE/confirm").status_code == 404


def test_confirm_order_exito():
    r = client.post("/orders/O001/confirm")
    assert r.status_code == 200
    assert r.json()["status"] == "CONFIRMED"


def test_confirm_order_409_conflicto():
    client.post("/orders/O002/confirm")
    assert client.post("/orders/O002/confirm").status_code == 409


def test_confirm_pedido_vacio_422():
    assert client.post("/orders/O007/confirm").status_code == 422


def test_confirm_cliente_inactivo_422():
    assert client.post("/orders/O003/confirm").status_code == 422


def test_ship_sin_guia_422():
    client.post("/orders/O012/confirm")
    r = client.post("/orders/O012/ship", json={"tracking_number": "  "})
    assert r.status_code == 422


def test_flujo_completo_hasta_entregado():
    assert client.post("/orders/O016/confirm").status_code == 200
    assert client.post("/orders/O016/ship", json={"tracking_number": "G1"}).status_code == 200
    r = client.post("/orders/O016/deliver")
    assert r.status_code == 200
    assert r.json()["status"] == "DELIVERED"


def test_cancel_desde_shipped_409():
    client.post("/orders/O014/confirm")
    client.post("/orders/O014/ship", json={"tracking_number": "G1"})
    r = client.post("/orders/O014/cancel", json={"reason": "x"})
    assert r.status_code == 409


def test_return_desde_shipped():
    client.post("/orders/O015/confirm")
    client.post("/orders/O015/ship", json={"tracking_number": "G1"})
    r = client.post("/orders/O015/return")
    assert r.status_code == 200
    assert r.json()["status"] == "RETURNED"
