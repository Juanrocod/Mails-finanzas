from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.routers import auth, uploads, orders, dashboard
from app.routers import audit as audit_router
from app.routers import session as session_router

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="Gestión de Órdenes Bursátiles", version="1.0.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(uploads.router)
app.include_router(orders.router)
app.include_router(dashboard.router)
app.include_router(audit_router.router)
app.include_router(session_router.router)


@app.get("/health")
def health():
    return {"status": "ok"}
