# El Campus

Sistema de caja, inventario y pedidos para El Campus (Bar, Grill, Fun & Market).
Supermercado entre semana, restaurante los fines de semana.

Ver [`docs/plan.md`](docs/plan.md) para la arquitectura, el modelo de datos y
el plan de trabajo por fases (documento vivo).

## Backend

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate   # PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Docs interactivas de la API en `http://127.0.0.1:8000/docs`.
