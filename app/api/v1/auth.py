from datetime import timedelta
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.security import OAuth2PasswordRequestForm

from app.core.database import get_database
from app.services.auth_service import AuthService
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    RefreshTokenRequest,
    LogoutRequest,
    PasswordResetRequest,
    PasswordResetConfirm
)
from app.dependencies.auth import get_current_user
from app.models.user import UserInDB

router = APIRouter(prefix="/auth", tags=["authentication"])

@router.post("/register", response_model=Dict[str, Any])
async def register(
    user_data: RegisterRequest,
    request: Request,
    db=Depends(get_database)
):
    """Registrar nuevo usuario"""
    auth_service = AuthService(db)
    user = await auth_service.create_user(user_data)
    
    return {
        "message": "User registered successfully",
        "user_id": str(user.id),
        "email": user.email,
        "requires_verification": not user.email_verified
    }

@router.post("/login", response_model=TokenResponse)
async def login(
    login_data: LoginRequest,
    request: Request,
    response: Response,
    db=Depends(get_database)
):
    """Iniciar sesión"""
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

@router.post("/login/form")
async def login_form(
    form_data: OAuth2PasswordRequestForm = Depends(),
    request: Request = None,
    db=Depends(get_database)
):
    """Login compatible con OAuth2 para herramientas como Swagger"""
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

@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: Request,
    response: Response,
    refresh_data: RefreshTokenRequest = None,
    db=Depends(get_database)
):
    """Refrescar tokens"""
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

@router.post("/logout")
async def logout(
    logout_data: LogoutRequest,
    request: Request,
    response: Response,
    current_user: UserInDB = Depends(get_current_user),
    db=Depends(get_database)
):
    """Cerrar sesión"""
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

@router.get("/me")
async def get_current_user_info(
    current_user: UserInDB = Depends(get_current_user)
):
    """Obtener información del usuario actual"""
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "full_name": current_user.full_name,
        "username": current_user.username,
        "role": current_user.role,
        "avatar_url": current_user.avatar_url,
        "email_verified": current_user.email_verified,
        "two_factor_enabled": current_user.two_factor_enabled,
        "created_at": current_user.created_at
    }

@router.post("/password/reset")
async def request_password_reset(
    reset_data: PasswordResetRequest,
    db=Depends(get_database)
):
    """Solicitar reset de contraseña"""
    auth_service = AuthService(db)
    user = await auth_service.get_user_by_email(reset_data.email)
    
    if user:
        # Generar token de reset (simplificado)
        token = auth_service._create_token(
            data={
                "sub": str(user.id),
                "type": "password_reset"
            },
            expires_delta=timedelta(hours=24)
        )
        
        # Aquí enviar email con el token
        print(f"Password reset token for {user.email}: {token}")
    
    # Siempre devolver mismo mensaje por seguridad
    return {"message": "If the email exists, a reset link has been sent"}

@router.post("/password/reset/confirm")
async def confirm_password_reset(
    confirm_data: PasswordResetConfirm,
    db=Depends(get_database)
):
    """Confirmar reset de contraseña"""
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