# El Campus

Sistema de caja, inventario y pedidos para El Campus (Bar, Grill, Fun & Market).
Supermercado entre semana, restaurante los fines de semana.

Ver [`docs/plan.md`](docs/plan.md) para la arquitectura, el modelo de datos y el
plan de trabajo por fases (documento vivo).

## Cómo está armado

```
backend/     API en FastAPI + SQLite. Una sola fuente de verdad.
apps/web/    App en React. Las tres pantallas viven aquí:
             caja (PC), mesas (celular del mesero) y admin.
docs/        Plan técnico.
```

Las tres pantallas son **una sola aplicación web**. La caja no es una app
aparte: es el navegador en pantalla completa (modo kiosco) en el PC del
mostrador, hablando con el servidor por `localhost`. Un solo código, una sola
estética, y el lector de código de barras funciona igual porque se comporta
como un teclado.

## Levantarlo en desarrollo

Hacen falta **dos terminales** de PowerShell abiertas al tiempo. No hay que
activar el entorno virtual: los comandos llaman directo a su Python.

**Terminal 1 · Servidor**

```powershell
cd C:\Users\samla\Desktop\ELCAMPUS\backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

**Terminal 2 · App web**

```powershell
cd C:\Users\samla\Desktop\ELCAMPUS\apps\web
npm run dev
```

Luego abre http://localhost:5173. La documentación de la API queda en
http://127.0.0.1:8000/docs.

**Solo la primera vez** (o cuando quieras empezar la base desde cero), carga
datos de prueba antes de levantar el servidor:

```powershell
cd C:\Users\samla\Desktop\ELCAMPUS\backend
.\.venv\Scripts\python.exe seed.py
```

Crea tres usuarios de desarrollo — `admin`, `vendedor` y `mesero`, todos con
clave `campus123`. **Antes de usarlo en el negocio hay que crear los usuarios
reales y borrar estos.**

> En Windows PowerShell 5.1 el `&&` no existe: cada comando va en su propia
> línea. Y si VS Code intenta activar el entorno virtual solo y sale un error
> de paréntesis, ignóralo — estos comandos no lo necesitan.

## Pruebas

```powershell
cd C:\Users\samla\Desktop\ELCAMPUS\backend
.\.venv\Scripts\python.exe -m pytest
```

## En el negocio (producción)

```bash
cd apps/web && npm run build
cd backend && .venv/Scripts/python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Compilada, la app web la entrega el mismo servidor: un solo proceso y un solo
puerto. La caja abre `http://localhost:8000` y los celulares del salón entran
por la IP del PC. El administrador remoto entra por Tailscale, no por un
puerto abierto a internet.
