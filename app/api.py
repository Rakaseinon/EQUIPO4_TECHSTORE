from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from cargar_csv import load_fixture
from app.domain import DomainException, InvalidOrderData, InvalidOrderTransition
from app.specifications import discount_rate

app = FastAPI(title="TechStore U4")
orders = load_fixture()


class ShipPayload(BaseModel):
    tracking_number: str


class CancelPayload(BaseModel):
    reason: str


def _get_order_or_404(order_id: str):
    order = orders.get(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    return order


def _run(action):
    """Ejecuta una operación del dominio y traduce sus errores a HTTP.

    409 -> transición no permitida; 422 -> datos inválidos.
    Aquí NO se repiten validaciones de negocio.
    """
    try:
        action()
    except InvalidOrderTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except InvalidOrderData as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except DomainException as exc:
        raise HTTPException(status_code=422, detail=str(exc))


def _summary(order):
    return {"id": order.id, "status": order.status.value}


@app.get("/orders/{order_id}")
def get_order(order_id: str):
    order = _get_order_or_404(order_id)
    return {
        "id": order.id,
        "customer_id": order.customer.id,
        "status": order.status.value,
        "units": order.units,
        "total": str(order.total.amount),  # texto: evita perder precisión con float
        "discount_rate": str(discount_rate(order)),
        "has_promotion": order.has_promotion,
        "events": [e.name for e in order.events],
    }


@app.post("/orders/{order_id}/confirm")
def confirm_order(order_id: str):
    order = _get_order_or_404(order_id)
    _run(order.confirm)
    return _summary(order)


@app.post("/orders/{order_id}/ship")
def ship_order(order_id: str, payload: ShipPayload):
    order = _get_order_or_404(order_id)
    _run(lambda: order.ship(payload.tracking_number))
    return _summary(order)


@app.post("/orders/{order_id}/cancel")
def cancel_order(order_id: str, payload: CancelPayload):
    order = _get_order_or_404(order_id)
    _run(lambda: order.cancel(payload.reason))
    return _summary(order)


@app.post("/orders/{order_id}/deliver")
def deliver_order(order_id: str):
    order = _get_order_or_404(order_id)
    _run(order.deliver)
    return _summary(order)


@app.post("/orders/{order_id}/return")
def return_order(order_id: str):
    order = _get_order_or_404(order_id)
    _run(order.return_order)
    return _summary(order)
