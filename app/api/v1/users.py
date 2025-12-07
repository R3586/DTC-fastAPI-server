from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query

from app.core.database import get_database
from app.services.user_service import UserService
from app.models.user import UserPublic, UserUpdate, UserRole
from app.dependencies.auth import get_current_user, get_current_admin, get_current_superadmin
from app.schemas.auth import RegisterRequest

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/", response_model=List[UserPublic])
async def get_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    role: Optional[UserRole] = None,
    current_user=Depends(get_current_admin),
    db=Depends(get_database)
):
    """Obtener lista de usuarios (admin only)"""
    user_service = UserService(db)
    return await user_service.get_users(skip, limit, role)

@router.get("/{user_id}", response_model=UserPublic)
async def get_user(
    user_id: str,
    current_user=Depends(get_current_user),
    db=Depends(get_database)
):
    """Obtener usuario por ID"""
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

@router.put("/{user_id}", response_model=UserPublic)
async def update_user(
    user_id: str,
    update_data: UserUpdate,
    current_user=Depends(get_current_user),
    db=Depends(get_database)
):
    """Actualizar usuario"""
    user_service = UserService(db)
    return await user_service.update_user(user_id, update_data, current_user)

@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    current_user=Depends(get_current_user),
    db=Depends(get_database)
):
    """Eliminar usuario (soft delete)"""
    user_service = UserService(db)
    await user_service.delete_user(user_id, current_user)
    return {"message": "User deleted successfully"}

@router.patch("/{user_id}/role")
async def update_user_role(
    user_id: str,
    new_role: UserRole,
    current_user=Depends(get_current_admin),
    db=Depends(get_database)
):
    """Actualizar rol de usuario (admin only)"""
    user_service = UserService(db)
    await user_service.update_role(user_id, new_role, current_user)
    return {"message": "Role updated successfully"}

@router.get("/me/sessions")
async def get_my_sessions(
    current_user=Depends(get_current_user),
    db=Depends(get_database)
):
    """Obtener sesiones activas del usuario actual"""
    from services.auth_service import AuthService
    auth_service = AuthService(db)
    sessions = await auth_service.get_user_sessions(str(current_user.id))
    
    # Formatear respuesta
    formatted_sessions = []
    for session in sessions:
        formatted_sessions.append({
            "id": str(session["_id"]),
            "platform": session.get("platform"),
            "device_name": session.get("device_name"),
            "location": session.get("location"),
            "last_active": session["last_active"],
            "created_at": session["created_at"]
        })
    
    return formatted_sessions