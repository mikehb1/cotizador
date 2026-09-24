# Cotizador y Control de Vehículos

Sistema local de cotizaciones para taller/negocio de vehículos (estilo ECOEXPRES). Guarda clientes, vehículos, historial y cotizaciones en una base SQLite local.

## Requisitos
- **Para usar el ejecutable (recomendado):** nada. Doble clic y listo.
- **Para correr desde el código:** Python 3 (solo usa la librería estándar, no instala nada).

## Cómo usarlo

### Opción 1 — Ejecutable `.exe` (sin instalar Python)
1. Doble clic en `dist\Cotizador.exe` (o cópialo a cualquier carpeta/PC).
2. Se abre el navegador en `http://localhost:8080`.
3. La base de datos (`cotizador.db`) se crea **junto al .exe**, así tus datos viajan con el programa.

### Opción 2 — Desde el código
1. Doble clic en `iniciar.bat` (o `python server.py` en terminal).
2. Se abre el navegador en `http://localhost:8080`.

## Funciones
- **Clientes y Vehículos**: registra el vehículo con los datos del dueño en una sola pantalla (un cliente puede tener varios vehículos).
- **Historial**: cada vehículo guarda su historial de cotizaciones.
- **Cotizaciones**: con folio consecutivo, partidas con folio/código de producto, total automático (Subtotal + IVA 16%).
- **Impresión**: hoja en formato papel (estilo ECOEXPRES) lista para imprimir.
- **Envío por correo**: abre el cliente de correo con la cotización lista.
- **Productos**: catálogo con folio/código, descripción, categoría y precio.
- **Respaldo/Restaurar**: exporta e importa toda la base.
- **Responsive**: funciona en teléfono y computadora.

## Estructura
- `server.py` — servidor HTTP local + SQLite (solo stdlib)
- `index.html` — interfaz web
- `logo.png` — logo de la empresa (transparente)
- `iniciar.bat` — lanzador de doble clic (usa Python)
- `compilar_exe.bat` — genera el `.exe` con PyInstaller
- `dist\Cotizador.exe` — ejecutable independiente de Windows
- `cotizador.db` — base de datos (se crea sola)

## Nota sobre el `.exe` y Windows Smart App Control
El ejecutable **no está firmado digitalmente** (firmar cuesta un certificado). En PCs con
**Smart App Control** activo (Windows 11) Windows lo puede bloquear con el mensaje
"Una directiva de Control de aplicaciones bloqueó este archivo". Eso no es un error del
programa; es una política de seguridad. Soluciones:
- Clic derecho → **Propiedades** → marcar **Desbloquear** (si aparece).
- Usar la **Opción 2** (Python) en esa PC, o correr el `.exe` en una PC sin esa política.
