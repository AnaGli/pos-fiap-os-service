from fastapi import FastAPI

from app.api.routes.orders import router as orders_router

app = FastAPI(title="OS Service", version="0.1.0")
app.include_router(orders_router)


@app.get("/health", tags=["Health"])
def health():
    return {"status": "healthy"}
