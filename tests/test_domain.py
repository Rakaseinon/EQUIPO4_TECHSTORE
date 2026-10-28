import pytest
from decimal import Decimal

from app.domain import (
    Money, Order, Customer, OrderItem, OrderStatus,
    InvalidOrderData, InvalidOrderTransition, OrderItemLimitExceeded,
)
from app.specifications import (
    ten_percent_discount, five_percent_discount, any_discount, discount_rate,
    MinimumAmountSpec, VIPCustomerSpec, MinimumUnitsSpec, ActivePromotionSpec,
)
from cargar_csv import load_fixture


def _pedido_con_items(vip=True, promo=False, unidades=5, precio="1100"):
    """Pedido de prueba armado a mano (preparar datos)."""
    order = Order(Customer("CX", is_vip=vip), "OX", has_promotion=promo)
    order.add_item(OrderItem("SKU", unidades, Money(Decimal(precio))))
    return order


# ---------- Value Objects ----------
def test_money_negativo():
    with pytest.raises(InvalidOrderData):
        Money(Decimal("-10.00"))


def test_money_add_monedas_distintas():
    with pytest.raises(InvalidOrderData):
        Money(Decimal("1"), "MXN").add(Money(Decimal("1"), "USD"))


def test_money_es_inmutable():
    m = Money(Decimal("5"))
    with pytest.raises(Exception):
        m.amount = Decimal("6")


def test_orderitem_cantidad_cero():
    with pytest.raises(InvalidOrderData):
        OrderItem("SKU001", 0, Money(Decimal("10")))


# ---------- Carga de datos ----------
def test_pedido_o001_inicia_draft():
    orders = load_fixture()
    assert orders["O001"].status.value == "DRAFT"
    assert orders["O001"].units == 4
    assert orders["O001"].total.amount == Decimal("2100.00")


def test_se_cargan_16_pedidos_en_draft():
    orders = load_fixture()
    assert len(orders) == 16
    assert all(o.status == OrderStatus.DRAFT for o in orders.values())


# ---------- Límite de 20 unidades ----------
def test_limite_20_unidades():
    order = Order(Customer(id="C100"), "O100")
    with pytest.raises(OrderItemLimitExceeded):
        order.add_item(OrderItem("SKU01", 21, Money(Decimal("10.00"))))


def test_limite_cuenta_unidades_no_renglones():
    order = load_fixture()["O009"]  # 19 unidades en un solo renglón
    with pytest.raises(OrderItemLimitExceeded):
        order.add_item(OrderItem("SKU003", 2, Money(Decimal("120.00"))))
    assert order.units == 19  # no se modificó nada


def test_20_unidades_exactas_se_permiten():
    order = load_fixture()["O008"]
    order.confirm()
    assert order.status == OrderStatus.CONFIRMED


# ---------- Confirmación ----------
def test_cliente_inactivo_no_confirma():
    order = load_fixture()["O003"]
    with pytest.raises(InvalidOrderData):
        order.confirm()
    assert order.status == OrderStatus.DRAFT
    assert order.events == []


def test_pedido_vacio_no_confirma():
    order = load_fixture()["O007"]
    with pytest.raises(InvalidOrderData):
        order.confirm()
    assert order.status == OrderStatus.DRAFT


def test_doble_confirmacion_lanza_excepcion():
    order = load_fixture()["O013"]
    order.confirm()
    assert order.status.value == "CONFIRMED"
    assert len(order.events) == 1
    with pytest.raises(InvalidOrderTransition):
        order.confirm()
    assert len(order.events) == 1  # el segundo intento NO agrega evento


def test_no_se_agregan_items_despues_de_confirmar():
    order = load_fixture()["O013"]
    order.confirm()
    with pytest.raises(InvalidOrderTransition):
        order.add_item(OrderItem("SKU001", 1, Money(Decimal("600"))))


# ---------- Envío, cancelación, entrega, devolución ----------
@pytest.mark.parametrize("guia", ["", "   "])
def test_envio_sin_guia(guia):
    order = load_fixture()["O012"]
    order.confirm()
    with pytest.raises(InvalidOrderData):
        order.ship(guia)
    assert order.status == OrderStatus.CONFIRMED
    assert [e.name for e in order.events] == ["OrderConfirmed"]


def test_cancelacion_desde_shipped_rechazada():
    order = load_fixture()["O014"]
    order.confirm()
    order.ship("GUIA123")
    with pytest.raises(InvalidOrderTransition):
        order.cancel("ya no lo quiero")
    assert order.status == OrderStatus.SHIPPED
    assert [e.name for e in order.events] == ["OrderConfirmed", "OrderShipped"]


def test_cancelacion_sin_motivo():
    order = load_fixture()["O002"]
    order.confirm()
    with pytest.raises(InvalidOrderData):
        order.cancel("")
    assert order.status == OrderStatus.CONFIRMED


def test_cancelacion_valida_desde_confirmed():
    order = load_fixture()["O002"]
    order.confirm()
    order.cancel("cambio de opinión")
    assert order.status == OrderStatus.CANCELLED
    assert order.events[-1].name == "OrderCancelled"


def test_entrega_valida():
    order = load_fixture()["O016"]
    order.confirm()
    order.ship("GUIA1")
    order.deliver()
    assert order.status == OrderStatus.DELIVERED
    assert [e.name for e in order.events] == [
        "OrderConfirmed", "OrderShipped", "OrderDelivered"]


def test_devolucion_valida():
    order = load_fixture()["O015"]
    order.confirm()
    order.ship("GUIA1")
    order.return_order()
    assert order.status == OrderStatus.RETURNED
    assert order.events[-1].name == "OrderReturned"


def test_no_se_entrega_desde_draft():
    order = load_fixture()["O016"]
    with pytest.raises(InvalidOrderTransition):
        order.deliver()


# ---------- Specifications y descuentos ----------
def test_descuento_10_porcentaje():
    orders = load_fixture()
    assert ten_percent_discount.is_satisfied_by(orders["O001"]) is True
    assert ten_percent_discount.is_satisfied_by(orders["O005"]) is False  # promo activa


def test_descuento_5_porcentaje():
    orders = load_fixture()
    assert five_percent_discount.is_satisfied_by(orders["O006"]) is True
    assert five_percent_discount.is_satisfied_by(orders["O001"]) is False


@pytest.mark.parametrize("pedido, esperado", [
    ("O001", "0.10"),  # E01
    ("O002", "0"),     # E02
    ("O005", "0"),     # E04 promoción activa
    ("O006", "0.05"),  # E05
    ("O010", "0"),     # E09 total exactamente 500 (umbral estricto)
    ("O011", "0"),     # E10 solo 3 unidades
])
def test_discount_rate_escenarios(pedido, esperado):
    assert discount_rate(load_fixture()[pedido]) == Decimal(esperado)


def test_prioridad_10_sobre_5():
    order = _pedido_con_items(vip=True, promo=False, unidades=5, precio="1100")  # 5500
    assert ten_percent_discount.is_satisfied_by(order)
    assert five_percent_discount.is_satisfied_by(order)
    assert discount_rate(order) == Decimal("0.10")


def test_any_discount_or():
    orders = load_fixture()
    assert any_discount.is_satisfied_by(orders["O001"])      # solo la de 10 %
    assert any_discount.is_satisfied_by(orders["O006"])      # solo la de 5 %
    assert not any_discount.is_satisfied_by(orders["O002"])  # ninguna


def test_monto_minimo_es_estricto():
    order = load_fixture()["O010"]  # total exactamente 500
    assert MinimumAmountSpec(Decimal("500")).is_satisfied_by(order) is False


def test_unidades_minimas_incluye_el_limite():
    order = load_fixture()["O001"]  # 4 unidades
    assert MinimumUnitsSpec(4).is_satisfied_by(order) is True


def test_specifications_no_modifican_el_pedido():
    order = load_fixture()["O001"]
    antes = (order.status, order.units, order.total.amount, len(order.events))
    ten_percent_discount.is_satisfied_by(order)
    assert antes == (order.status, order.units, order.total.amount, len(order.events))


def test_not_spec():
    order = load_fixture()["O005"]
    assert ActivePromotionSpec().is_satisfied_by(order) is True
    assert (~ActivePromotionSpec()).is_satisfied_by(order) is False
    assert VIPCustomerSpec().is_satisfied_by(order) is True
