from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query

from app.core.database import get_database
from app.application.services.user_service import UserService
from app.domain.models.user import UserPublic, UserUpdate, UserRole, UserInDB
from app.core.dependencies import get_current_user, get_current_admin

router = APIRouter(prefix="/users", tags=["users"])


# ========== LISTAR USUARIOS (Admin only) ==========
@router.get("/", response_model=List[UserPublic])
async def get_users(
    skip: int = Query(0, ge=0, description="Número de registros a saltar"),
    limit: int = Query(100, ge=1, le=1000, description="Límite de registros"),
    role: Optional[UserRole] = Query(None, description="Filtrar por rol"),
    status: Optional[str] = Query(None, description="Filtrar por estado"),
    search: Optional[str] = Query(None, description="Buscar por email o nombre"),
    current_user: UserInDB = Depends(get_current_admin),
    db=Depends(get_database)
):
    """
    Obtener lista de usuarios (Solo administradores)
    
    Permisos requeridos: ADMIN o SUPERADMIN
    """
    user_service = UserService(db)
    
    # Construir query
    query = {}
    if role:
        query["role"] = role
    if status:
        query["status"] = status
    if search:
        query["$or"] = [
            {"email": {"$regex": search, "$options": "i"}},
            {"full_name": {"$regex": search, "$options": "i"}},
            {"username": {"$regex": search, "$options": "i"}}
        ]
    
    users = await db.users.find(query).skip(skip).limit(limit).to_list(limit)
    
    # Convertir a modelos
    return [UserPublic(**user) for user in users]


# ========== OBTENER USUARIO POR ID ==========
@router.get("/{user_id}", response_model=UserPublic)
async def get_user(
    user_id: str,
    current_user: UserInDB = Depends(get_current_user),
    db=Depends(get_database)
):
    """
    Obtener usuario por ID
    
    - Usuarios normales solo pueden ver su propio perfil
    - Administradores pueden ver cualquier perfil
    """
    user_service = UserService(db)
    user = await user_service.get_user(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Solo admin o el propio usuario puede ver
    if user_id != str(current_user.id) and current_user.role not in [UserRole.ADMIN, UserRole.SUPERADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    return user


# ========== ACTUALIZAR USUARIO ==========
@router.put("/{user_id}", response_model=UserPublic)
async def update_user(
    user_id: str,
    update_data: UserUpdate,
    current_user: UserInDB = Depends(get_current_user),
    db=Depends(get_database)
):
    """
    Actualizar información de usuario
    
    - Usuarios normales solo pueden actualizar su propio perfil
    - Administradores pueden actualizar cualquier perfil
    """
    user_service = UserService(db)
    return await user_service.update_user(user_id, update_data, current_user)


# ========== ELIMINAR USUARIO (Soft delete) ==========
@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    current_user: UserInDB = Depends(get_current_user),
    db=Depends(get_database)
):
    """
    Eliminar usuario (soft delete)
    
    - Marca al usuario como inactivo
    - No elimina físicamente los datos
    - Solo admin o el propio usuario puede eliminar
    - No se puede eliminar superadmin
    """
    user_service = UserService(db)
    await user_service.delete_user(user_id, current_user)
    return {"message": "User deleted successfully"}


# ========== CAMBIAR ROL DE USUARIO (Admin only) ==========
@router.patch("/{user_id}/role")
async def update_user_role(
    user_id: str,
    new_role: UserRole,
    current_user: UserInDB = Depends(get_current_admin),
    db=Depends(get_database)
):
    """
    Actualizar rol de usuario (Solo administradores)
    
    Permisos requeridos: ADMIN o SUPERADMIN
    """
    user_service = UserService(db)
    await user_service.update_role(user_id, new_role, current_user)
    return {"message": "Role updated successfully"}


# ========== ACTIVAR/DESACTIVAR USUARIO (Admin only) ==========
@router.patch("/{user_id}/status")
async def update_user_status(
    user_id: str,
    status: str = Query(..., regex="^(active|inactive|suspended)$"),
    current_user: UserInDB = Depends(get_current_admin),
    db=Depends(get_database)
):
    """
    Cambiar estado de usuario (Solo administradores)
    
    Estados posibles: active, inactive, suspended
    """
    from bson import ObjectId
    
    # No permitir desactivar superadmin
    if status != "active":
        user = await db.users.find_one({"_id": ObjectId(user_id)})
        if user and user.get("role") == UserRole.SUPERADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot deactivate superadmin"
            )
    
    await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"status": status, "is_active": status == "active"}}
    )
    
    return {"message": f"User status updated to {status}"}


# ========== ESTADÍSTICAS DE USUARIOS (Admin only) ==========
@router.get("/stats/summary")
async def get_user_stats(
    current_user: UserInDB = Depends(get_current_admin),
    db=Depends(get_database)
):
    """
    Obtener estadísticas de usuarios (Solo administradores)
    
    Retorna conteos por rol, estado y actividad
    """
    # Conteo por rol
    role_stats = await db.users.aggregate([
        {"$group": {
            "_id": "$role",
            "count": {"$sum": 1},
            "active": {"$sum": {"$cond": [{"$eq": ["$is_active", True]}, 1, 0]}}
        }}
    ]).to_list(None)
    
    # Conteo por estado
    status_stats = await db.users.aggregate([
        {"$group": {
            "_id": "$status",
            "count": {"$sum": 1}
        }}
    ]).to_list(None)
    
    # Usuarios nuevos últimos 7 días
    seven_days_ago = datetime.utcnow() - datetime.timedelta(days=7)
    new_users = await db.users.count_documents({
        "created_at": {"$gte": seven_days_ago}
    })
    
    # Usuarios activos últimos 24 horas
    one_day_ago = datetime.utcnow() - datetime.timedelta(days=1)
    active_users = await db.sessions.count_documents({
        "last_active": {"$gte": one_day_ago},
        "status": "active"
    })
    
    return {
        "total_users": await db.users.count_documents({}),
        "role_distribution": role_stats,
        "status_distribution": status_stats,
        "new_users_last_7_days": new_users,
        "active_users_last_24h": active_users,
        "timestamp": datetime.utcnow().isoformat()
    }


# ========== BUSCAR USUARIOS (Admin only) ==========
@router.get("/search/{query}")
async def search_users(
    query: str,
    limit: int = Query(20, ge=1, le=100),
    current_user: UserInDB = Depends(get_current_admin),
    db=Depends(get_database)
):
    """
    Buscar usuarios por email, nombre o username (Solo administradores)
    """
    users = await db.users.find({
        "$or": [
            {"email": {"$regex": query, "$options": "i"}},
            {"full_name": {"$regex": query, "$options": "i"}},
            {"username": {"$regex": query, "$options": "i"}}
        ]
    }).limit(limit).to_list(limit)
    
    return [UserPublic(**user) for user in users]