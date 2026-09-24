# Cotizador y Control de Vehículos

Sistema local de cotizaciones para taller/negocio de vehículos (estilo ECOEXPRES). Guarda clientes, vehículos, historial y cotizaciones en una base SQLite local.

## Requisitos
- Python 3 (solo usa la librería estándar, no instala nada)

## Cómo usarlo
1. Doble clic en `iniciar.bat` (o `python server.py` en terminal).
2. Se abre el navegador en `http://localhost:8080`.
3. La base de datos se guarda automáticamente en `cotizador.db`.

## Funciones
- **Clientes y Vehículos**: registra el vehículo con los datos del dueño en una sola pantalla (un cliente puede tener varios vehículos).
- **Historial**: cada vehículo guarda su historial de cotizaciones.
- **Cotizaciones**: con folio consecutivo, partidas con folio/código de producto, total automático.
- **Impresión**: hoja en formato papel (estilo ECOEXPRES) lista para imprimir.
- **Envío por correo**: abre el cliente de correo con la cotización lista.
- **Productos**: catálogo con folio/código, descripción, categoría y precio.
- **Respaldo/Restaurar**: exporta e importa toda la base.
- **Responsive**: funciona en teléfono y computadora.

## Estructura
- `server.py` — servidor HTTP local + SQLite (solo stdlib)
- `index.html` — interfaz web
- `iniciar.bat` — lanzador de doble clic
- `cotizador.db` — base de datos (se crea sola)
