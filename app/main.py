from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.v1.router import api_router
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS: le dice al navegador qué frontends pueden consumir esta API.
# Solo se autorizan los orígenes listados en CORS_ORIGINS (.env); no se usa "*".
# El token viaja en la cabecera Authorization (no en cookies), por eso
# allow_credentials=False.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
    max_age=600,  # el navegador recuerda el preflight 10 minutos
)

app.include_router(health_router)
app.include_router(api_router, prefix=settings.api_v1_prefix)
