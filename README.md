# TechStore U4 – Núcleo de negocio

Práctica guiada de la Actividad 4 (Componentes de Lógica de Negocio, FIME · UANL).
Administra pedidos de una tienda ficticia: carga datos desde CSV, aplica reglas de
descuento con el patrón Specification, controla el estado de cada pedido con eventos
de dominio y expone operaciones mediante una API REST con FastAPI.
Los datos viven en memoria; al cerrar el programa los cambios se pierden.

## Requisitos
- Python 3.11 o superior

## Instalación
```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# Windows CMD:        .venv\Scripts\activate.bat
# macOS / Linux:      source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Ejecución
```bash
python cargar_csv.py                 # carga los 16 pedidos y los imprime
python correr_escenarios.py          # ejecuta los 15 escenarios E01-E15
python ejercicio_o013.py             # confirma O013 dos veces
uvicorn app.api:app --reload         # levanta la API
```
Documentación interactiva: http://127.0.0.1:8000/docs  
Contrato OpenAPI: http://127.0.0.1:8000/openapi.json

## Pruebas
```bash
python -m pytest -q
```

## Estructura
```
datos/              CSV de clientes, productos, pedidos, detalle y escenarios
cargar_csv.py       Cargador de datos (fixtures)
correr_escenarios.py  Ejecuta los escenarios de datos/escenarios.csv
ejercicio_o013.py   Ejercicio de la doble confirmación de O013
requirements.txt    Dependencias del proyecto
app/domain.py       Money, Customer, OrderItem, Order, DomainEvent y excepciones
app/specifications.py  Specifications (AND, OR, NOT) y reglas de descuento
app/api.py          API REST con FastAPI
tests/              Pruebas pytest del dominio y de la API
```

## Reglas de negocio
- `Money` es inmutable, usa `Decimal` y rechaza montos negativos.
- Un pedido admite como máximo **20 unidades** (suma de cantidades, no número de renglones).
- Solo un pedido en `DRAFT` admite artículos.
- **Descuento 10 %:** cliente VIP, total > 500 MXN, al menos 4 unidades y sin promoción activa.
- **Descuento 5 %:** total > 5000 MXN y sin promoción activa.
- Si se cumplen ambas reglas, tiene prioridad el 10 %.
- Estados: `DRAFT → CONFIRMED → SHIPPED → DELIVERED`; desde `CONFIRMED` se puede cancelar
  (`CANCELLED`) y desde `SHIPPED` se puede devolver (`RETURNED`).
- Confirmar exige artículos y cliente activo; enviar exige guía no vacía; cancelar exige motivo.
- Los eventos (`OrderConfirmed`, `OrderShipped`, `OrderCancelled`, `OrderDelivered`,
  `OrderReturned`) se registran solo después de una transición válida.

## Endpoints
| Método | Ruta | Descripción | Respuestas |
| --- | --- | --- | --- |
| GET | `/orders/{id}` | Consulta un pedido | 200, 404 |
| POST | `/orders/{id}/confirm` | Confirma el pedido | 200, 404, 409, 422 |
| POST | `/orders/{id}/ship` | Envía (body: `tracking_number`) | 200, 404, 409, 422 |
| POST | `/orders/{id}/cancel` | Cancela (body: `reason`) | 200, 404, 409, 422 |
| POST | `/orders/{id}/deliver` | Marca como entregado | 200, 404, 409 |
| POST | `/orders/{id}/return` | Marca como devuelto | 200, 404, 409 |

Códigos: **404** pedido inexistente, **409** transición no permitida, **422** datos inválidos.

## Evidencias
Las capturas (carga de pedidos, pytest y Swagger), la bitácora de los escenarios
E01–E15 y el diagrama de estados están en la carpeta `evidencias/`.
