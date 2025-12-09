from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status, Query
from typing import Optional
from datetime import datetime

from app.core.dependencies import get_current_user
from app.domain.models.user import UserInDB, UserProfileUpdate, UserProfile
from app.application.services.user_service import UserService
from app.application.services.file_service import FileService
from app.core.database import get_database

router = APIRouter(prefix="/profile", tags=["profile"])


# ========== OBTENER PERFIL COMPLETO ==========
@router.get("/", response_model=UserProfile)
async def get_profile(
    current_user: UserInDB = Depends(get_current_user),
    db=Depends(get_database)
):
    """
    Obtener perfil completo del usuario actual
    
    Incluye información básica y estadísticas
    """
    user_service = UserService(db)
    file_service = FileService(db)
    
    # Obtener información básica del usuario
    user_profile = UserProfile(**current_user.model_dump())
    
    # Obtener estadísticas adicionales
    files = await file_service.get_user_files(current_user.id, limit=5)
    user_profile.total_files = await db.files.count_documents({
        "user_id": current_user.id
    })
    
    # Obtener última actividad de sesión
    last_session = await db.sessions.find_one(
        {"user_id": current_user.id},
        sort=[("last_active", -1)]
    )
    
    if last_session:
        user_profile.last_active = last_session.get("last_active")
    
    return user_profile


# ========== ACTUALIZAR PERFIL ==========
@router.put("/", response_model=UserProfile)
async def update_profile(
    profile_data: UserProfileUpdate,
    current_user: UserInDB = Depends(get_current_user),
    db=Depends(get_database)
):
    """
    Actualizar información del perfil
    
    Campos actualizables:
    - full_name
    - username
    - bio
    - website
    - location
    """
    user_service = UserService(db)
    
    updated_user = await user_service.update_profile(
        user_id=current_user.id,
        update_data=profile_data,
        current_user=current_user
    )
    
    return UserProfile(**updated_user.model_dump())


# ========== SUBIR AVATAR ==========
@router.post("/avatar", response_model=dict)
async def upload_avatar(
    file: UploadFile = File(..., description="Image file (JPEG, PNG, WebP)"),
    public: bool = Form(True, description="Make avatar publicly accessible"),
    current_user: UserInDB = Depends(get_current_user),
    db=Depends(get_database)
):
    """
    Subir o actualizar avatar de perfil
    
    - **file**: Imagen (max 5MB, JPEG/PNG/WebP)
    - **public**: Si el avatar debe ser público
    - La imagen se procesa automáticamente (redimensiona, recorta, crea thumbnail)
    """
    file_service = FileService(db)
    
    result = await file_service.upload_avatar(
        user=current_user,
        file=file,
        public=public
    )
    
    return {
        "message": "Avatar uploaded successfully",
        "avatar_url": result["avatar_url"],
        "avatar_thumbnail_url": result["avatar_thumbnail_url"],
        "avatar_size": result["avatar_size"],
        "thumbnail_size": result["thumbnail_size"],
        "original_filename": result["original_filename"]
    }


# ========== ELIMINAR AVATAR ==========
@router.delete("/avatar")
async def delete_avatar(
    current_user: UserInDB = Depends(get_current_user),
    db=Depends(get_database)
):
    """
    Eliminar avatar del perfil
    
    Remueve tanto el avatar como el thumbnail
    """
    file_service = FileService(db)
    
    success = await file_service.delete_avatar(current_user)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not delete avatar"
        )
    
    return {"message": "Avatar deleted successfully"}


# ========== INFORMACIÓN DE ALMACENAMIENTO ==========
@router.get("/storage")
async def get_storage_info(
    current_user: UserInDB = Depends(get_current_user),
    db=Depends(get_database)
):
    """
    Obtener información de almacenamiento del usuario
    
    Retorna:
    - Storage total usado
    - Cantidad de archivos
    - Distribución por tipo de archivo
    - Archivos recientes
    """
    file_service = FileService(db)
    
    # Obtener archivos del usuario
    files = await file_service.get_user_files(current_user.id)
    
    # Calcular estadísticas por tipo de archivo
    stats = await db.files.aggregate([
        {"$match": {"user_id": current_user.id}},
        {"$group": {
            "_id": {"$arrayElemAt": [{"$split": ["$content_type", "/"]}, 0]},
            "count": {"$sum": 1},
            "total_size": {"$sum": "$size"}
        }}
    ]).to_list(None)
    
    total_files = await db.files.count_documents({"user_id": current_user.id})
    
    return {
        "user_id": current_user.id,
        "storage_used": current_user.storage_used,
        "storage_used_mb": round(current_user.storage_used / (1024 * 1024), 2),
        "total_files": total_files,
        "file_types": stats,
        "recent_files": files[:10]  # Últimos 10 archivos
    }


# ========== ACTIVIDAD RECIENTE ==========
@router.get("/activity")
async def get_recent_activity(
    limit: int = Query(20, ge=1, le=100),
    current_user: UserInDB = Depends(get_current_user),
    db=Depends(get_database)
):
    """
    Obtener actividad reciente del usuario
    
    Incluye:
    - Inicios de sesión
    - Subida de archivos
    - Actualizaciones de perfil
    """
    # Obtener últimos inicios de sesión
    login_activity = await db.sessions.find(
        {"user_id": current_user.id},
        sort=[("last_active", -1)],
        limit=limit
    ).to_list(limit)
    
    # Obtener últimos archivos subidos
    file_activity = await db.files.find(
        {"user_id": current_user.id},
        sort=[("uploaded_at", -1)],
        limit=limit
    ).to_list(limit)
    
    # Formatear respuesta
    activity = []
    
    for session in login_activity:
        activity.append({
            "type": "login",
            "timestamp": session.get("last_active"),
            "device": session.get("device_name"),
            "platform": session.get("platform"),
            "ip": session.get("ip_address")
        })
    
    for file in file_activity:
        activity.append({
            "type": "file_upload",
            "timestamp": file.get("uploaded_at"),
            "filename": file.get("original_name"),
            "size": file.get("size"),
            "content_type": file.get("content_type")
        })
    
    # Ordenar por timestamp
    activity.sort(key=lambda x: x["timestamp"] or datetime.min, reverse=True)
    
    return {
        "total_activities": len(activity),
        "activities": activity[:limit]
    }


# ========== CAMBIAR CONTRASEÑA ==========
@router.post("/change-password")
async def change_password(
    old_password: str = Form(...),
    new_password: str = Form(...),
    current_user: UserInDB = Depends(get_current_user),
    db=Depends(get_database)
):
    """
    Cambiar contraseña del usuario
    
    - **old_password**: Contraseña actual
    - **new_password**: Nueva contraseña (mínimo 8 caracteres)
    """
    from app.application.services.auth_service import AuthService
    
    auth_service = AuthService(db)
    
    success = await auth_service.change_password(
        str(current_user.id),
        old_password,
        new_password
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not change password"
        )
    
    return {"message": "Password changed successfully"}


# ========== CONFIGURACIONES DE NOTIFICACIONES ==========
@router.get("/notifications/settings")
async def get_notification_settings(
    current_user: UserInDB = Depends(get_current_user),
    db=Depends(get_database)
):
    """
    Obtener configuraciones de notificaciones del usuario
    """
    # Por ahora solo marketing_emails
    return {
        "marketing_emails": current_user.marketing_emails,
        "email_verified": current_user.email_verified
    }


@router.put("/notifications/settings")
async def update_notification_settings(
    marketing_emails: Optional[bool] = Form(None),
    current_user: UserInDB = Depends(get_current_user),
    db=Depends(get_database)
):
    """
    Actualizar configuraciones de notificaciones
    """
    from bson import ObjectId
    
    update_data = {}
    if marketing_emails is not None:
        update_data["marketing_emails"] = marketing_emails
    
    if update_data:
        update_data["updated_at"] = datetime.utcnow()
        await db.users.update_one(
            {"_id": ObjectId(current_user.id)},
            {"$set": update_data}
        )
    
    return {"message": "Notification settings updated"}


# ========== EXPORTAR DATOS ==========
@router.get("/export")
async def export_user_data(
    current_user: UserInDB = Depends(get_current_user),
    db=Depends(get_database)
):
    """
    Exportar todos los datos del usuario (GDPR compliance)
    
    Retorna un JSON con toda la información del usuario
    """
    # Obtener datos del usuario
    user_data = await db.users.find_one({"_id": current_user.id})
    
    # Obtener sesiones
    sessions = await db.sessions.find(
        {"user_id": current_user.id}
    ).to_list(None)
    
    # Obtener archivos
    files = await db.files.find(
        {"user_id": current_user.id}
    ).to_list(None)
    
    # Limpiar datos sensibles
    if user_data:
        user_data.pop("hashed_password", None)
        user_data["_id"] = str(user_data["_id"])
    
    for session in sessions:
        session["_id"] = str(session["_id"])
        session["user_id"] = str(session["user_id"])
        session.pop("refresh_token", None)
    
    for file in files:
        file["_id"] = str(file["_id"])
        file["user_id"] = str(file["user_id"])
    
    return {
        "user": user_data,
        "sessions": sessions,
        "files": files,
        "exported_at": datetime.utcnow().isoformat(),
        "data_points": len(sessions) + len(files) + 1
    }