import asyncio
from fastapi import APIRouter, Depends, Query, BackgroundTasks
from typing import Optional
from datetime import datetime, timedelta

from app.core.dependencies import get_current_superadmin
from app.domain.models.user import UserInDB, UserRole
from app.core.database import get_database
from app.utils.logger import logger

router = APIRouter(prefix="/admin", tags=["administration"])


# ========== DASHBOARD ==========
@router.get("/dashboard")
async def admin_dashboard(
    current_user: UserInDB = Depends(get_current_superadmin),
    db=Depends(get_database)
):
    """
    Dashboard de administración (Solo SUPERADMIN)
    Retorna estadísticas globales del sistema
    """
    # Estadísticas de usuarios
    total_users = await db.users.count_documents({})
    active_users = await db.users.count_documents({"is_active": True})
    new_users_today = await db.users.count_documents({
        "created_at": {"$gte": datetime.utcnow() - timedelta(days=1)}
    })
    
    # Estadísticas de archivos
    total_files = await db.files.count_documents({})
    total_storage = await db.files.aggregate([
        {"$group": {"_id": None, "total": {"$sum": "$size"}}}
    ]).to_list(None)
    
    total_storage_gb = round((total_storage[0]["total"] if total_storage else 0) / (1024**3), 2)
    
    # Estadísticas de sesiones
    active_sessions = await db.sessions.count_documents({
        "status": "active",
        "last_active": {"$gte": datetime.utcnow() - timedelta(minutes=30)}
    })
    
    # Últimos 5 usuarios registrados
    recent_users = await db.users.find(
        {},
        sort=[("created_at", -1)],
        limit=5
    ).to_list(5)
    
    # Últimos 10 archivos subidos
    recent_files = await db.files.find(
        {},
        sort=[("uploaded_at", -1)],
        limit=10
    ).to_list(10)
    
    return {
        "system": {
            "total_users": total_users,
            "active_users": active_users,
            "new_users_today": new_users_today,
            "total_files": total_files,
            "total_storage_gb": total_storage_gb,
            "active_sessions": active_sessions,
            "uptime": "N/A",  # Podrías integrar con un sistema de monitoreo
        },
        "recent_activity": {
            "users": recent_users,
            "files": recent_files
        },
        "timestamp": datetime.utcnow().isoformat()
    }


# ========== LIMPIAR TOKENS EXPIRADOS ==========
@router.post("/cleanup/tokens")
async def cleanup_expired_tokens(
    background_tasks: BackgroundTasks,
    current_user: UserInDB = Depends(get_current_superadmin),
    db=Depends(get_database)
):
    """
    Limpiar tokens expirados de la blacklist y sesiones
    """
    from app.application.services.auth_service import AuthService
    
    auth_service = AuthService(db)
    
    # Ejecutar en background
    background_tasks.add_task(auth_service.cleanup_expired_tokens)
    
    return {"message": "Cleanup task scheduled"}


# ========== BACKUP DE BASE DE DATOS ==========
@router.post("/backup/database")
async def backup_database(
    background_tasks: BackgroundTasks,
    current_user: UserInDB = Depends(get_current_superadmin),
    db=Depends(get_database)
):
    """
    Iniciar backup de la base de datos
    """
    # Esta función debería implementarse según tu infraestructura
    # Por ahora es solo un placeholder
    
    async def perform_backup():
        logger.info("Starting database backup...")
        # Implementar lógica de backup aquí
        # Ej: mongodump, subir a S3, etc.
        await asyncio.sleep(1)  # Simular trabajo
        logger.info("Database backup completed")
    
    background_tasks.add_task(perform_backup)
    
    return {"message": "Backup task scheduled"}


# ========== LOGS DEL SISTEMA ==========
@router.get("/logs")
async def get_system_logs(
    level: Optional[str] = Query(None, regex="^(INFO|WARNING|ERROR|DEBUG)$"),
    limit: int = Query(100, ge=1, le=1000),
    current_user: UserInDB = Depends(get_current_superadmin),
    db=Depends(get_database)
):
    """
    Obtener logs del sistema (si estás usando una colección de logs)
    """
    query = {}
    if level:
        query["level"] = level
    
    logs = await db.logs.find(
        query,
        sort=[("timestamp", -1)],
        limit=limit
    ).to_list(limit)
    
    return {
        "total_logs": await db.logs.count_documents(query),
        "logs": logs
    }


# ========== CONFIGURACIÓN DEL SISTEMA ==========
@router.get("/settings")
async def get_system_settings(
    current_user: UserInDB = Depends(get_current_superadmin),
    db=Depends(get_database)
):
    """
    Obtener configuración del sistema
    """
    from app.config import settings
    
    # Retornar configuración no sensible
    return {
        "app_name": settings.APP_NAME,
        "app_version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "debug": settings.DEBUG,
        "storage_provider": settings.STORAGE_PROVIDER,
        "storage_bucket": settings.STORAGE_BUCKET,
        "avatar_max_size_mb": settings.AVATAR_MAX_SIZE_MB,
        "rate_limit_enabled": settings.RATE_LIMIT_ENABLED,
        "rate_limit_requests": settings.RATE_LIMIT_REQUESTS,
        "rate_limit_period": settings.RATE_LIMIT_PERIOD,
    }


# ========== MONITOREO DE SALUD ==========
@router.get("/health/detailed")
async def detailed_health_check(
    current_user: UserInDB = Depends(get_current_superadmin),
    db=Depends(get_database)
):
    """
    Verificación detallada de salud del sistema
    """
    health_status = {
        "timestamp": datetime.utcnow().isoformat(),
        "services": {}
    }
    
    # Verificar MongoDB
    try:
        await db.command("ping")
        health_status["services"]["mongodb"] = {
            "status": "healthy",
            "latency": "N/A"
        }
    except Exception as e:
        health_status["services"]["mongodb"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    # Verificar Storage
    try:
        from app.core.storage import storage_client
        # Intentar una operación simple
        if hasattr(storage_client, 'client'):
            health_status["services"]["storage"] = {
                "status": "healthy",
                "provider": storage_client.provider
            }
        else:
            health_status["services"]["storage"] = {
                "status": "unhealthy",
                "error": "Storage client not initialized"
            }
    except Exception as e:
        health_status["services"]["storage"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    # Calcular estado general
    all_healthy = all(
        service["status"] == "healthy" 
        for service in health_status["services"].values()
    )
    
    health_status["overall"] = "healthy" if all_healthy else "unhealthy"
    
    return health_status