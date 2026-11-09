from fastapi import FastAPI

from app.api.routes import router
from app.db import Base, engine

app = FastAPI(title="inventory-service")
app.include_router(router)


@app.on_event("startup")
def create_tables():
    Base.metadata.create_all(engine)


@app.get("/health")
def health():
    return {"status": "ok"}
