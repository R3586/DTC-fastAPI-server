from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict
import secrets
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import HTTPException, status, Request
from bson import ObjectId

from app.core.config import settings
from app.models.user import UserInDB
from app.models.session import UserSession, SessionPlatform
from app.models.token import TokenBlacklist, TokenType
from app.schemas.auth import LoginRequest, RegisterRequest

class AuthService:
    def __init__(self, db):
        self.db = db
        self.pwd_context = CryptContext(
            schemes=["bcrypt"],
            deprecated="auto",
            bcrypt__rounds=12
        )
    
    # ========== USER MANAGEMENT ==========
    
    async def create_user(self, user_data: RegisterRequest) -> UserInDB:
        """Crear nuevo usuario"""
        # Verificar si el email ya existe
        existing = await self.db.users.find_one({"email": user_data.email})
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Verificar username si se proporciona
        if user_data.username:
            existing = await self.db.users.find_one({"username": user_data.username})
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already taken"
                )
        
        # Crear usuario
        user_dict = user_data.model_dump(exclude={"password"})
        user_dict["hashed_password"] = self.get_password_hash(user_data.password)
        user_dict["created_at"] = datetime.utcnow()
        user_dict["updated_at"] = datetime.utcnow()
        user_dict["_id"] = ObjectId()  # Usar ObjectId nativo para MongoDB
        
        result = await self.db.users.insert_one(user_dict)
        
        # Enviar email de verificación
        await self.send_verification_email(user_data.email)
        
        return await self.get_user_by_id(str(result.inserted_id))
    
    async def get_user_by_email(self, email: str) -> Optional[UserInDB]:
        user = await self.db.users.find_one({"email": email})
        if user:
            # Convertir ObjectId a string para el modelo
            user["_id"] = str(user["_id"])
            return UserInDB(**user)
        return None
    
    async def get_user_by_id(self, user_id: str) -> Optional[UserInDB]:
        try:
            user = await self.db.users.find_one({"_id": ObjectId(user_id)})
            if user:
                user["_id"] = str(user["_id"])
                return UserInDB(**user)
            return None
        except:
            return None
    
    # ========== PASSWORD MANAGEMENT ==========
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return self.pwd_context.verify(plain_password, hashed_password)
    
    def get_password_hash(self, password: str) -> str:
        if len(password) > 72:
            password = password[:72]
        return self.pwd_context.hash(password)
    
    async def change_password(self, user_id: str, old_password: str, new_password: str) -> bool:
        user = await self.get_user_by_id(user_id)
        if not user:
            return False
        
        if not self.verify_password(old_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Incorrect old password"
            )
        
        await self.db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {
                "hashed_password": self.get_password_hash(new_password),
                "updated_at": datetime.utcnow()
            }}
        )
        
        # Invalidar todas las sesiones excepto la actual
        await self.revoke_all_sessions(user_id, exclude_current=True)
        
        return True
    
    # ========== TOKEN MANAGEMENT ==========
    
    async def login(self, login_data: LoginRequest, request: Request) -> Tuple[str, str, Dict]:
        """Autenticar usuario y crear tokens"""
        user = await self.get_user_by_email(login_data.email)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is inactive"
            )
        
        if not self.verify_password(login_data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"
            )
        
        # Determinar plataforma
        user_agent = request.headers.get("user-agent", "")
        platform = self.detect_platform(user_agent)
        
        # Crear tokens
        access_token, refresh_token, jti = await self.create_tokens(
            str(user.id),
            remember_me=login_data.remember_me
        )
        
        # Crear sesión
        session_dict = UserSession(
            user_id=str(user.id),
            session_token=jti,
            refresh_token=refresh_token,
            user_agent=user_agent[:500],
            ip_address=request.client.host if request.client else None,
            platform=platform,
            device_id=login_data.device_id,
            device_name=login_data.device_name,
            expires_at=datetime.utcnow() + timedelta(
                days=settings.REFRESH_TOKEN_EXPIRE_DAYS_LONG 
                if login_data.remember_me 
                else settings.REFRESH_TOKEN_EXPIRE_DAYS
            )
        ).model_dump(by_alias=True)
        
        # Usar ObjectId para MongoDB
        session_dict["_id"] = ObjectId()
        session_dict["user_id"] = ObjectId(str(user.id))
        
        await self.db.sessions.insert_one(session_dict)
        
        # Actualizar usuario
        await self.db.users.update_one(
            {"_id": ObjectId(str(user.id))},
            {"$set": {
                "last_login": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            },
             "$inc": {"login_count": 1}}
        )
        
        user_data = {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "avatar_url": user.avatar_url,
            "email_verified": user.email_verified
        }
        
        return access_token, refresh_token, user_data
    
    async def create_tokens(self, user_id: str, remember_me: bool = False) -> Tuple[str, str, str]:
        """Crear access token y refresh token con JTI"""
        # JTI (JWT ID) único para tracking
        jti = secrets.token_hex(32)
        
        # Access Token (corto)
        access_token_expire = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = self._create_token(
            data={
                "sub": user_id,
                "type": "access",
                "jti": jti
            },
            expires_delta=access_token_expire
        )
        
        # Refresh Token (largo)
        if remember_me:
            refresh_expire = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS_LONG)
        else:
            refresh_expire = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        
        refresh_token = self._create_token(
            data={
                "sub": user_id,
                "type": "refresh",
                "jti": jti
            },
            expires_delta=refresh_expire
        )
        
        return access_token, refresh_token, jti
    
    def _create_token(self, data: dict, expires_delta: timedelta) -> str:
        to_encode = data.copy()
        expire = datetime.utcnow() + expires_delta
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "iss": settings.APP_NAME
        })
        return jwt.encode(
            to_encode,
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM
        )
    
    async def verify_token(self, token: str, token_type: str = "access") -> Optional[dict]:
        """Verificar token y chequear blacklist"""
        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM]
            )
            
            if payload.get("type") != token_type:
                return None
            
            # Verificar si está en blacklist
            blacklisted = await self.db.token_blacklist.find_one({"token": token})
            if blacklisted:
                return None
            
            return payload
            
        except JWTError:
            return None
    
    async def refresh_tokens(self, refresh_token: str, request: Request) -> Tuple[str, str, str]:
        """Generar nuevos tokens a partir de refresh token"""
        payload = await self.verify_token(refresh_token, "refresh")
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        user_id = payload.get("sub")
        jti = payload.get("jti")
        
        if not user_id or not jti:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        
        # Verificar sesión
        session = await self.db.sessions.find_one({
            "session_token": jti,
            "status": "active"
        })
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session not found or revoked"
            )
        
        # Verificar si el token ha expirado
        if datetime.utcnow() > session["expires_at"]:
            await self.db.sessions.update_one(
                {"_id": session["_id"]},
                {"$set": {"status": "expired"}}
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session expired"
            )
        
        # Invalidar el refresh token viejo
        await self.blacklist_token(refresh_token, TokenType.REFRESH, user_id)
        
        # Crear nuevos tokens
        new_access_token, new_refresh_token, new_jti = await self.create_tokens(
            user_id,
            remember_me=True  # Mantener configuración de remember_me
        )
        
        # Actualizar sesión
        await self.db.sessions.update_one(
            {"_id": session["_id"]},
            {"$set": {
                "session_token": new_jti,
                "refresh_token": new_refresh_token,
                "last_active": datetime.utcnow(),
                "expires_at": datetime.utcnow() + timedelta(
                    days=settings.REFRESH_TOKEN_EXPIRE_DAYS_LONG
                )
            }}
        )
        
        return new_access_token, new_refresh_token, user_id
    
    async def blacklist_token(self, token: str, token_type: TokenType, user_id: Optional[str] = None):
        """Añadir token a blacklist"""
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            expires_at = datetime.fromtimestamp(payload["exp"])
        except:
            expires_at = datetime.utcnow() + timedelta(days=1)
        
        blacklist_entry = TokenBlacklist(
            token=token,
            token_type=token_type,
            user_id=user_id,
            expires_at=expires_at
        ).model_dump(by_alias=True)
        
        blacklist_entry["_id"] = ObjectId()
        if user_id:
            blacklist_entry["user_id"] = ObjectId(user_id)
        
        await self.db.token_blacklist.insert_one(blacklist_entry)
    
    # ========== SESSION MANAGEMENT ==========
    
    async def logout(self, user_id: str, refresh_token: Optional[str] = None, logout_all: bool = False):
        """Cerrar sesión(es)"""
        if logout_all:
            # Invalidar todas las sesiones del usuario
            sessions = await self.db.sessions.find({
                "user_id": ObjectId(user_id),
                "status": "active"
            }).to_list(None)
            
            for session in sessions:
                await self.blacklist_token(
                    session["refresh_token"],
                    TokenType.REFRESH,
                    user_id
                )
            
            await self.db.sessions.update_many(
                {"user_id": ObjectId(user_id), "status": "active"},
                {"$set": {"status": "revoked"}}
            )
        elif refresh_token:
            # Invalidar solo una sesión
            session = await self.db.sessions.find_one({
                "refresh_token": refresh_token,
                "status": "active"
            })
            
            if session:
                await self.blacklist_token(refresh_token, TokenType.REFRESH, user_id)
                await self.db.sessions.update_one(
                    {"_id": session["_id"]},
                    {"$set": {"status": "revoked"}}
                )
    
    async def revoke_all_sessions(self, user_id: str, exclude_current: bool = False, current_jti: Optional[str] = None):
        """Revocar todas las sesiones excepto quizás la actual"""
        query = {
            "user_id": ObjectId(user_id),
            "status": "active"
        }
        
        if exclude_current and current_jti:
            query["session_token"] = {"$ne": current_jti}
        
        sessions = await self.db.sessions.find(query).to_list(None)
        
        for session in sessions:
            await self.blacklist_token(
                session["refresh_token"],
                TokenType.REFRESH,
                user_id
            )
        
        update_query = {
            "user_id": ObjectId(user_id),
            "status": "active"
        }
        
        if exclude_current and current_jti:
            update_query["session_token"] = {"$ne": current_jti}
        
        await self.db.sessions.update_many(
            update_query,
            {"$set": {"status": "revoked"}}
        )
    
    async def get_user_sessions(self, user_id: str):
        """Obtener todas las sesiones activas del usuario"""
        sessions = await self.db.sessions.find({
            "user_id": ObjectId(user_id),
            "status": "active"
        }).sort("last_active", -1).to_list(None)
        
        # Convertir ObjectId a strings
        for session in sessions:
            session["_id"] = str(session["_id"])
            session["user_id"] = str(session["user_id"])
        
        return sessions
    
    # ========== HELPER METHODS ==========
    
    def detect_platform(self, user_agent: str) -> SessionPlatform:
        """Detectar plataforma desde user-agent"""
        user_agent_lower = user_agent.lower()
        
        if "mobile" in user_agent_lower:
            if "iphone" in user_agent_lower or "ipad" in user_agent_lower:
                return SessionPlatform.IOS
            elif "android" in user_agent_lower:
                return SessionPlatform.ANDROID
            return SessionPlatform.ANDROID
        elif "mozilla" in user_agent_lower or "chrome" in user_agent_lower or "safari" in user_agent_lower:
            return SessionPlatform.WEB
        else:
            return SessionPlatform.DESKTOP
    
    async def send_verification_email(self, email: str):
        """Enviar email de verificación (placeholder)"""
        # Implementar envío real de email
        print(f"Verification email sent to {email}")
    
    async def cleanup_expired_tokens(self):
        """Limpiar tokens expirados de la blacklist"""
        await self.db.token_blacklist.delete_many({
            "expires_at": {"$lt": datetime.utcnow()}
        })
        
        await self.db.sessions.delete_many({
            "expires_at": {"$lt": datetime.utcnow()}
        })