"""
DTC Backend - Main Application
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import JSONResponse
import time

from app.core.config import settings
from app.core.database import database
from app.api.middlewares import setup_middlewares
from app.api.errors import setup_exception_handlers
from app.api.v1 import api_v1_router
from app.utils.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan manager para manejar startup/shutdown events
    """
    # ========== STARTUP ==========
    logger.info("🚀  Desplegando DTC Server...")
    
    # Conectar a la base de datos
    try:
        await database.connect()
        logger.info("✅  BD conectado exitosamente")
    except Exception as e:
        logger.error(f"❌  Fallo al conectar con la BD: {e}")
        raise
    
    # Inicializar storage (se inicializa automáticamente al importar)
    from app.core.storage import storage_client
    logger.info(f"✅  Almacenamiento inicializado. Proveedor: {storage_client.provider}")
    
    yield
    
    # ========== SHUTDOWN ==========
    logger.info("🛑  Cerrando DTC Server...")
    
    # Desconectar de la base de datos
    await database.disconnect()
    logger.info("🛑  BD desconectado exitosamente")


# Crear aplicación FastAPI
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    openapi_url="/api/v1/openapi.json" if settings.DEBUG else None,
    docs_url="/api/docs" if settings.DEBUG else None,
    redoc_url="/api/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
    swagger_ui_parameters={
        "syntaxHighlight.theme": "monokai",
        "tryItOutEnabled": True,
        "displayRequestDuration": True,
    }
)


# ========== CONFIGURAR MIDDLEWARES ==========
setup_middlewares(app)


# ========== CONFIGURAR HANDLERS DE ERRORES ==========
setup_exception_handlers(app)


# ========== INCLUIR ROUTERS ==========
app.include_router(api_v1_router, prefix="/api")


# ========== RUTAS GLOBALES ==========
@app.get("/")
async def root():
    """
    Página principal de la API
    """
    return {
        "message": f"Welcome to {settings.APP_NAME} API",
        "version": settings.APP_VERSION,
        "autor": "Evan",
        "environment": settings.ENVIRONMENT,
        "docs": "/api/docs" if settings.DEBUG else None,
        "health": "/health",
        "status": "operational"
    }


@app.get("/health")
async def health_check():
    """
    Health check del sistema
    
    Verifica que todos los servicios estén funcionando correctamente
    """
    health_status = {
        "status": "healthy",
        "timestamp": time.time(),
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "checks": {}
    }
    
    # Verificar MongoDB
    try:
        await database.db.command("ping")
        health_status["checks"]["mongodb"] = {
            "status": "healthy",
            "latency": "N/A"
        }
    except Exception as e:
        health_status["checks"]["mongodb"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "degraded"
    
    # Verificar Storage
    try:
        from app.core.storage import storage_client
        # Intentar operación simple
        if hasattr(storage_client, 'client'):
            health_status["checks"]["storage"] = {
                "status": "healthy",
                "provider": storage_client.provider
            }
        else:
            health_status["checks"]["storage"] = {
                "status": "unhealthy",
                "error": "Storage client not initialized"
            }
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["checks"]["storage"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "degraded"
    
    return health_status


@app.get("/info")
async def system_info():
    """
    Información del sistema
    
    Retorna información técnica sobre la API y configuración
    """
    from app.core.config import settings
    
    return {
        "app": {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
            "debug": settings.DEBUG,
        },
        "api": {
            "version": "v1",
            "base_path": "/api/v1",
            "docs_available": settings.DEBUG,
        },
        "database": {
            "type": "mongodb",
            "name": settings.MONGODB_DB_NAME,
        },
        "storage": {
            "provider": settings.STORAGE_PROVIDER,
            "bucket": settings.STORAGE_BUCKET,
        },
        "security": {
            "jwt_enabled": True,
            "access_token_expiry_minutes": settings.ACCESS_TOKEN_EXPIRE_MINUTES,
            "refresh_token_expiry_days": settings.REFRESH_TOKEN_EXPIRE_DAYS,
        }
    }


# ========== MANEJADOR PARA RUTAS NO ENCONTRADAS ==========
@app.get("/{full_path:path}")
async def catch_all(full_path: str):
    """
    Manejador para rutas no encontradas
    
    Proporciona una respuesta útil para rutas no definidas
    """
    return JSONResponse(
        status_code=404,
        content={
            "error": "Endpoint not found",
            "message": f"The requested path '/{full_path}' does not exist",
            "suggestions": [
                "Check the API documentation at /api/docs",
                "Verify the endpoint path and HTTP method",
                "Ensure you're using the correct API version (/api/v1/)"
            ]
        }
    )


# ========== PUNTO DE ENTRADA PRINCIPAL ==========
if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info",
        workers=settings.WORKERS if not settings.DEBUG else 1,
        access_log=True,
    )