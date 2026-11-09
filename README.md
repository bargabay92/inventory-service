# inventory-service

FastAPI + SQLAlchemy 1.4 service on Pydantic v1. Warehouses, products, stock levels and reservations.
Uses the shared `orders-common` library (sibling repo) for its base schema, field types and event envelope.

Why this repo is a harder migration than a single service:
- `orders-common==1.4.0` requires `pydantic<2`, so it must be migrated and released first.
- `fastapi==0.95.2` only supports Pydantic v1 (v2 support starts at FastAPI 0.100).
- `BaseSettings` moved to the separate `pydantic-settings` package in v2.
- Schemas read SQLAlchemy rows with `orm_mode` / `from_orm` (v2: `from_attributes` / `model_validate`).

```bash
pip install -r requirements.txt   # orders-common from the internal index, or: pip install -e ../orders-common
pytest -q
```
