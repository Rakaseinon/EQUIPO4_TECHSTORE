"""Ejecuta los 15 escenarios de datos/escenarios.csv sobre el dominio.

Cada caso se corre con pedidos recién cargados desde load_fixture(), así que
ningún caso depende del resultado de otro. Ejecutar desde la carpeta que
contiene 'datos' y este archivo:

    python correr_escenarios.py
"""
from decimal import Decimal

from cargar_csv import load_fixture, rows
from app.domain import DomainException, Money, OrderItem
from app.specifications import discount_rate


def precio(sku):
    return next(Decimal(p["precio_mxn"]) for p in rows("productos.csv") if p["sku"] == sku)


def pasos_de(accion, order):
    """Devuelve la lista de pasos (nombre, función) que describe cada acción."""
    confirmar = ("confirmar", order.confirm)
    enviar = ("enviar", lambda: order.ship("GUIA-001"))
    pasos = {
        "confirmar": [confirmar],
        "agregar SKU003 x2": [("agregar SKU003 x2",
                               lambda: order.add_item(OrderItem("SKU003", 2, Money(precio("SKU003")))))],
        "confirmar y enviar sin guia": [confirmar, ("enviar sin guia", lambda: order.ship(""))],
        "confirmar dos veces": [confirmar, ("segunda confirmacion", order.confirm)],
        "confirmar, enviar y cancelar": [confirmar, enviar,
                                         ("cancelar", lambda: order.cancel("cambio de opinion"))],
        "confirmar, enviar y devolver": [confirmar, enviar, ("devolver", order.return_order)],
        "confirmar, enviar y entregar": [confirmar, enviar, ("entregar", order.deliver)],
    }
    return pasos[accion]


def ejecutar(accion, order):
    if accion == "evaluar_descuento":
        return f"{int(discount_rate(order) * 100)}%"
    for nombre, paso in pasos_de(accion, order):
        try:
            paso()
        except DomainException as exc:
            return f"rechazo en '{nombre}' ({type(exc).__name__})"
    return "exito"


def main():
    for caso in rows("escenarios.csv"):
        order = load_fixture()[caso["pedido_id"]]
        resultado = ejecutar(caso["accion"], order)
        eventos = [e.name for e in order.events]
        print(f'{caso["caso_id"]} | {caso["accion"]} | {resultado} | '
              f'estado final={order.status.value} | eventos={eventos}')


if __name__ == "__main__":
    main()
