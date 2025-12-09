"""
FastAPI dependencies for the application
"""

from typing import Optional, Tuple
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .config import settings
from .security import decode_token
from .database import get_database
from app.domain.models.user import UserInDB, UserRole
from app.application.services.auth_service import AuthService

security = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    token: Optional[str] = None
) -> UserInDB:
    """
    Obtener usuario actual desde token JWT
    
    Busca token en:
    1. Parámetro `token` (para WebSocket, etc.)
    2. Authorization header
    3. Cookie `access_token`
    """
    # Prioridad: token param > Authorization header > cookie
    if token:
        auth_token = token
    elif credentials:
        auth_token = credentials.credentials
    else:
        auth_token = request.cookies.get("access_token")
    
    if not auth_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verificar token
    payload = decode_token(auth_token)
    if not payload or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )
    
    # Obtener usuario de la base de datos
    db = await get_database()
    auth_service = AuthService(db)
    
    user = await auth_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )
    
    return user


async def get_current_active_user(
    current_user: UserInDB = Depends(get_current_user),
) -> UserInDB:
    """Verificar que el usuario esté activo"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user


def get_current_user_optional(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[UserInDB]:
    """
    Obtener usuario actual (opcional)
    
    Para endpoints públicos que pueden tener usuario autenticado o no
    """
    try:
        return get_current_user(request, credentials)
    except HTTPException:
        return None


# ========== ROLE-BASED DEPENDENCIES ==========

def require_role(required_role: UserRole):
    """
    Decorator factory para requerir un rol específico
    
    Usage:
        @router.get("/admin-only")
        async def admin_route(user = Depends(require_role(UserRole.ADMIN))):
            ...
    """
    async def role_checker(current_user: UserInDB = Depends(get_current_active_user)):
        # Jerarquía de roles
        role_hierarchy = {
            UserRole.GUEST: 0,
            UserRole.USER: 1,
            UserRole.MANAGER: 2,
            UserRole.ADMIN: 3,
            UserRole.SUPERADMIN: 4
        }
        
        current_role_level = role_hierarchy.get(current_user.role, 0)
        required_role_level = role_hierarchy.get(required_role, 0)
        
        if current_role_level < required_role_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires {required_role} role or higher"
            )
        
        return current_user
    
    return role_checker


# Shortcuts para roles comunes
get_current_user_role = require_role(UserRole.USER)
get_current_manager = require_role(UserRole.MANAGER)
get_current_admin = require_role(UserRole.ADMIN)
get_current_superadmin = require_role(UserRole.SUPERADMIN)


# ========== PERMISSION-BASED DEPENDENCIES ==========

def require_permission(permission: str):
    """
    Decorator factory para requerir un permiso específico
    
    (Para implementación futura de permisos granulares)
    """
    async def permission_checker(current_user: UserInDB = Depends(get_current_active_user)):
        # Aquí puedes implementar lógica de permisos más granular
        # Por ahora usamos solo roles
        return current_user
    
    return permission_checker


# ========== SESSION DEPENDENCIES ==========

async def get_current_session(
    request: Request,
    current_user: UserInDB = Depends(get_current_active_user)
) -> Tuple[UserInDB, dict]:
    """Obtener usuario y datos de sesión actual"""
    auth_token = request.cookies.get("access_token") or \
                 request.headers.get("authorization", "").replace("Bearer ", "")
    
    if auth_token:
        payload = decode_token(auth_token)
        session_data = payload or {}
    else:
        session_data = {}
    
    return current_user, session_data