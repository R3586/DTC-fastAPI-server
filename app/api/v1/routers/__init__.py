"""
Registro de todos los routers de la API v1
"""

from fastapi import APIRouter

from .auth import router as auth_router
from .users import router as users_router
from .profile import router as profile_router
from .files import router as files_router
from .admin import router as admin_router

# Crear router principal para v1
router = APIRouter()

# Registrar todos los routers
router.include_router(auth_router)
router.include_router(users_router)
router.include_router(profile_router)
router.include_router(files_router)
router.include_router(admin_router)

# Exportar
__all__ = ["router"]