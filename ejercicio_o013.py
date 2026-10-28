"""Ejercicio: confirmar el pedido O013 dos veces.

La primera confirmación cambia el estado a CONFIRMED y registra un evento.
La segunda lanza InvalidOrderTransition y NO agrega otro evento.
"""
from cargar_csv import load_fixture
from app.domain import InvalidOrderTransition

order = load_fixture()["O013"]
print("Inicial:", order.status.value, order.units, order.total.amount)

order.confirm()
print("Tras la 1.a confirmación:", order.status.value, [e.name for e in order.events])

try:
    order.confirm()
except InvalidOrderTransition as exc:
    print("2.a confirmación rechazada:", exc)

print("Estado final:", order.status.value, [e.name for e in order.events])
