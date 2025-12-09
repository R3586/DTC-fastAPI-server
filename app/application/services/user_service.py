import datetime
from typing import List, Optional
from fastapi import HTTPException, status
from bson import ObjectId

from app.domain.models.user import UserInDB, UserPublic, UserUpdate, UserRole

class UserService:
    def __init__(self, db):
        self.db = db
    
    async def get_users(
        self,
        skip: int = 0,
        limit: int = 100,
        role: Optional[UserRole] = None,
        status: Optional[str] = None
    ) -> List[UserPublic]:
        """Obtener lista de usuarios con filtros"""
        query = {}
        if role:
            query["role"] = role
        if status:
            query["status"] = status
        
        users = await self.db.users.find(query).skip(skip).limit(limit).to_list(limit)
        return [UserPublic(**user) for user in users]
    
    async def get_user(self, user_id: str) -> Optional[UserPublic]:
        """Obtener usuario por ID"""
        user = await self.db.users.find_one({"_id": ObjectId(user_id)})
        if user:
            return UserPublic(**user)
        return None
    
    async def update_user(
        self,
        user_id: str,
        update_data: UserUpdate,
        current_user: UserInDB
    ) -> UserPublic:
        """Actualizar usuario"""
        from datetime import datetime
        
        # Verificar permisos
        if user_id != str(current_user.id) and current_user.role not in [UserRole.ADMIN, UserRole.SUPERADMIN]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
        
        update_dict = update_data.dict(exclude_unset=True)
        update_dict["updated_at"] = datetime.utcnow()
        
        await self.db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": update_dict}
        )
        
        return await self.get_user(user_id)
    
    async def delete_user(self, user_id: str, current_user: UserInDB):
        """Eliminar usuario"""
        # Solo admin o el propio usuario puede eliminar
        if user_id != str(current_user.id) and current_user.role not in [UserRole.ADMIN, UserRole.SUPERADMIN]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
        
        # No permitir eliminar superadmin
        user = await self.db.users.find_one({"_id": ObjectId(user_id)})
        if user and user.get("role") == UserRole.SUPERADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot delete superadmin"
            )
        
        # Soft delete: marcar como inactivo
        await self.db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {
                "is_active": False,
                "status": "inactive",
                "updated_at": datetime.utcnow()
            }}
        )
    
    async def update_role(
        self,
        user_id: str,
        new_role: UserRole,
        current_user: UserInDB
    ):
        """Actualizar rol de usuario (solo admin)"""
        if current_user.role not in [UserRole.ADMIN, UserRole.SUPERADMIN]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin privileges required"
            )
        
        # No permitir modificar superadmin
        if user_id == str(current_user.id) and current_user.role == UserRole.SUPERADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot change own superadmin role"
            )
        
        await self.db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {
                "role": new_role,
                "updated_at": datetime.utcnow()
            }}
        )