from datetime import timedelta
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.security import OAuth2PasswordRequestForm

from app.core.database import get_database
from app.application.services.auth_service import AuthService
from app.domain.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    RefreshTokenRequest,
    LogoutRequest,
    PasswordResetRequest,
    PasswordResetConfirm
)
from app.core.dependencies import get_current_user
from app.domain.models.user import UserInDB

router = APIRouter(prefix="/auth", tags=["authentication"])

# ========== REGISTRO ==========
@router.post("/register", response_model=Dict[str, Any])
async def register(
    user_data: RegisterRequest,
    request: Request,
    db=Depends(get_database)
):
    """
    Registrar nuevo usuario
    
    - **email**: Email válido
    - **password**: Mínimo 8 caracteres, 1 mayúscula, 1 minúscula, 1 número
    - **full_name**: Nombre completo
    - **terms_accepted**: Debe aceptar términos
    """
    auth_service = AuthService(db)
    user = await auth_service.create_user(user_data)
    
    return {
        "message": "User registered successfully",
        "user_id": str(user.id),
        "email": user.email,
        "requires_verification": not user.email_verified
    }


# ========== LOGIN ==========
@router.post("/login", response_model=TokenResponse)
async def login(
    login_data: LoginRequest,
    request: Request,
    response: Response,
    db=Depends(get_database)
):
    """
    Iniciar sesión
    
    - **email**: Email registrado
    - **password**: Contraseña
    - **remember_me**: Mantener sesión activa (30 días vs 7 días)
    - **device_id**: ID único del dispositivo (opcional)
    - **device_name**: Nombre del dispositivo (opcional)
    """
    auth_service = AuthService(db)
    access_token, refresh_token, user_data = await auth_service.login(login_data, request)
    
    # Set cookies si es web
    if request.headers.get("user-agent", "").lower().find("mobile") == -1:
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=15 * 60  # 15 minutos
        )
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=True,
            samesite="strict",
            max_age=30 * 24 * 60 * 60 if login_data.remember_me else 7 * 24 * 60 * 60
        )
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=15 * 60,
        user_id=user_data["id"]
    )


# ========== LOGIN OAuth2 (para Swagger/Postman) ==========
@router.post("/login/form")
async def login_form(
    form_data: OAuth2PasswordRequestForm = Depends(),
    request: Request = None,
    db=Depends(get_database)
):
    """
    Login compatible con OAuth2 para herramientas como Swagger
    - **username**: Email
    - **password**: Contraseña
    """
    login_data = LoginRequest(
        email=form_data.username,
        password=form_data.password,
        remember_me=False
    )
    
    auth_service = AuthService(db)
    access_token, refresh_token, _ = await auth_service.login(login_data, request)
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


# ========== REFRESH TOKENS ==========
@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: Request,
    response: Response,
    refresh_data: RefreshTokenRequest = None,
    db=Depends(get_database)
):
    """
    Refrescar tokens de acceso
    
    - Puede enviarse refresh_token en body o cookie
    - Genera nuevos access_token y refresh_token
    """
    auth_service = AuthService(db)
    
    # Obtener refresh token de diferentes fuentes
    if refresh_data and refresh_data.refresh_token:
        refresh_token = refresh_data.refresh_token
    else:
        refresh_token = request.cookies.get("refresh_token")
    
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Refresh token required"
        )
    
    access_token, new_refresh_token, user_id = await auth_service.refresh_tokens(
        refresh_token, request
    )
    
    # Actualizar cookies si es web
    if request.headers.get("user-agent", "").lower().find("mobile") == -1:
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=15 * 60
        )
        response.set_cookie(
            key="refresh_token",
            value=new_refresh_token,
            httponly=True,
            secure=True,
            samesite="strict",
            max_age=30 * 24 * 60 * 60
        )
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        expires_in=15 * 60,
        user_id=user_id
    )


# ========== LOGOUT ==========
@router.post("/logout")
async def logout(
    logout_data: LogoutRequest,
    request: Request,
    response: Response,
    current_user: UserInDB = Depends(get_current_user),
    db=Depends(get_database)
):
    """
    Cerrar sesión
    
    - **refresh_token**: Token específico a invalidar (opcional)
    - **logout_all**: Invalidar TODAS las sesiones (default: False)
    """
    auth_service = AuthService(db)
    
    await auth_service.logout(
        str(current_user.id),
        logout_data.refresh_token,
        logout_data.logout_all
    )
    
    # Limpiar cookies
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    
    return {"message": "Logged out successfully"}


# ========== INFORMACIÓN DEL USUARIO ACTUAL ==========
@router.get("/me")
async def get_current_user_info(
    current_user: UserInDB = Depends(get_current_user)
):
    """
    Obtener información del usuario actual autenticado
    
    Retorna todos los datos del perfil del usuario
    """
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "full_name": current_user.full_name,
        "username": current_user.username,
        "role": current_user.role,
        "avatar_url": current_user.avatar_url,
        "avatar_thumbnail_url": current_user.avatar_thumbnail_url,
        "email_verified": current_user.email_verified,
        "two_factor_enabled": current_user.two_factor_enabled,
        "bio": current_user.bio,
        "website": current_user.website,
        "location": current_user.location,
        "created_at": current_user.created_at,
        "last_login": current_user.last_login,
        "login_count": current_user.login_count,
        "storage_used": current_user.storage_used
    }


# ========== RESET DE CONTRASEÑA ==========
@router.post("/password/reset")
async def request_password_reset(
    reset_data: PasswordResetRequest,
    db=Depends(get_database)
):
    """
    Solicitar reset de contraseña
    
    - **email**: Email del usuario
    - Envía email con link de reset (simulado en desarrollo)
    """
    auth_service = AuthService(db)
    user = await auth_service.get_user_by_email(reset_data.email)
    
    if user:
        # Generar token de reset
        token = auth_service._create_token(
            data={
                "sub": str(user.id),
                "type": "password_reset"
            },
            expires_delta=timedelta(hours=24)
        )
        
        # Aquí enviar email con el token (simulado)
        print(f"Password reset token for {user.email}: {token}")
    
    # Siempre devolver mismo mensaje por seguridad
    return {"message": "If the email exists, a reset link has been sent"}


@router.post("/password/reset/confirm")
async def confirm_password_reset(
    confirm_data: PasswordResetConfirm,
    db=Depends(get_database)
):
    """
    Confirmar reset de contraseña
    
    - **token**: Token recibido por email
    - **new_password**: Nueva contraseña
    """
    auth_service = AuthService(db)
    
    payload = await auth_service.verify_token(confirm_data.token, "password_reset")
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired token"
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token"
        )
    
    # Actualizar contraseña
    from bson import ObjectId
    hashed_password = auth_service.get_password_hash(confirm_data.new_password)
    
    await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"hashed_password": hashed_password}}
    )
    
    # Invalidar todas las sesiones
    await auth_service.revoke_all_sessions(user_id)
    
    return {"message": "Password updated successfully"}


# ========== VERIFICACIÓN DE EMAIL ==========
@router.post("/verify-email/request")
async def request_email_verification(
    current_user: UserInDB = Depends(get_current_user),
    db=Depends(get_database)
):
    """
    Solicitar reenvío de email de verificación
    
    Requiere autenticación
    """
    auth_service = AuthService(db)
    
    token = auth_service._create_token(
        data={
            "sub": str(current_user.id),
            "type": "email_verification"
        },
        expires_delta=timedelta(hours=24)
    )
    
    # Simular envío de email
    print(f"Email verification token for {current_user.email}: {token}")
    
    return {"message": "Verification email sent"}


@router.post("/verify-email/confirm")
async def confirm_email_verification(
    token: str,
    db=Depends(get_database)
):
    """
    Confirmar email con token
    
    - **token**: Token recibido por email
    """
    auth_service = AuthService(db)
    
    payload = await auth_service.verify_token(token, "email_verification")
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired token"
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token"
        )
    
    # Marcar email como verificado
    from bson import ObjectId
    await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"email_verified": True}}
    )
    
    return {"message": "Email verified successfully"}


# ========== SESIONES ACTIVAS ==========
@router.get("/sessions")
async def get_active_sessions(
    current_user: UserInDB = Depends(get_current_user),
    db=Depends(get_database)
):
    """
    Obtener todas las sesiones activas del usuario
    
    Retorna información de cada sesión (dispositivo, IP, última actividad)
    """
    auth_service = AuthService(db)
    sessions = await auth_service.get_user_sessions(str(current_user.id))
    
    return {
        "total_sessions": len(sessions),
        "sessions": sessions
    }


# ========== HEALTH CHECK DE AUTENTICACIÓN ==========
@router.get("/health")
async def auth_health_check():
    """
    Verificar estado del servicio de autenticación
    """
    return {
        "status": "healthy",
        "service": "authentication",
        "timestamp": datetime.utcnow().isoformat()
    }