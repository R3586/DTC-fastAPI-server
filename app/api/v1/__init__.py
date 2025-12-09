"""
API v1 - Punto de entrada principal
"""

from fastapi import APIRouter

from .routers import router

# Crear API router principal para v1
api_v1_router = APIRouter(prefix="/v1")

# Incluir todos los routers
api_v1_router.include_router(router)

# Exportar
__all__ = ["api_v1_router"]