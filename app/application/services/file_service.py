import io
from typing import Optional, Dict, Any
from fastapi import UploadFile, HTTPException, status
from datetime import datetime
from bson import ObjectId

from app.core.storage import storage_client
from app.utils.image_processor import image_processor
from app.utils.logger import logger
from app.config import settings
from app.domain.models.user import UserInDB


class FileService:
    """Servicio para manejo de archivos"""
    
    def __init__(self, db):
        self.db = db
    
    async def upload_avatar(
        self,
        user: UserInDB,
        file: UploadFile,
        public: bool = True
    ) -> Dict[str, Any]:
        """
        Subir y procesar avatar de usuario
        
        Args:
            user: Usuario actual
            file: Archivo de imagen
            public: Si el avatar debe ser público
        
        Returns:
            Información del avatar subido
        """
        # Validar imagen
        is_valid, error_msg = image_processor.validate_image(file)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        
        # Procesar imagen
        processed_images = image_processor.process_avatar(
            file,
            resize=True,
            crop_to_square=True,
            create_thumbnail=True
        )
        
        # Eliminar avatar anterior si existe
        if user.avatar_url:
            await self._delete_old_avatar(user)
        
        try:
            # Subir avatar principal (square o resized)
            if processed_images.get("square"):
                avatar_image = processed_images["square"]
            else:
                avatar_image = processed_images["resized"]
            
            avatar_file = UploadFile(
                filename="avatar.jpg",
                file=io.BytesIO(avatar_image["bytes"]),
                content_type="image/jpeg"
            )
            
            avatar_result = storage_client.upload_file(
                file=avatar_file,
                prefix=f"avatars/{user.id}/",
                public=public
            )
            
            # Subir thumbnail
            thumbnail_file = UploadFile(
                filename="thumbnail.jpg",
                file=io.BytesIO(processed_images["thumbnail"]["bytes"]),
                content_type="image/jpeg"
            )
            
            thumbnail_result = storage_client.upload_file(
                file=thumbnail_file,
                prefix=f"avatars/{user.id}/thumbnails/",
                public=public
            )
            
            # Actualizar usuario en la base de datos
            await self.db.users.update_one(
                {"_id": ObjectId(user.id)},
                {
                    "$set": {
                        "avatar_url": avatar_result["url"],
                        "avatar_thumbnail_url": thumbnail_result["url"],
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            logger.info(f"Avatar uploaded for user {user.id}")
            
            return {
                "avatar_url": avatar_result["url"],
                "avatar_thumbnail_url": thumbnail_result["url"],
                "avatar_size": avatar_image["size"],
                "thumbnail_size": processed_images["thumbnail"]["size"],
                "original_filename": file.filename
            }
            
        except Exception as e:
            logger.error(f"Error uploading avatar: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error uploading avatar"
            )
    
    async def _delete_old_avatar(self, user: UserInDB):
        """Eliminar avatar anterior del storage"""
        try:
            if user.avatar_url:
                # Extraer path del URL
                if settings.STORAGE_PUBLIC_URL and user.avatar_url.startswith(settings.STORAGE_PUBLIC_URL):
                    path = user.avatar_url.replace(f"{settings.STORAGE_PUBLIC_URL}/", "")
                    storage_client.delete_file(path)
                
                if user.avatar_thumbnail_url:
                    if settings.STORAGE_PUBLIC_URL and user.avatar_thumbnail_url.startswith(settings.STORAGE_PUBLIC_URL):
                        path = user.avatar_thumbnail_url.replace(f"{settings.STORAGE_PUBLIC_URL}/", "")
                        storage_client.delete_file(path)
        except Exception as e:
            logger.warning(f"Could not delete old avatar: {e}")
    
    async def delete_avatar(self, user: UserInDB) -> bool:
        """Eliminar avatar del usuario"""
        try:
            await self._delete_old_avatar(user)
            
            # Actualizar usuario
            await self.db.users.update_one(
                {"_id": ObjectId(user.id)},
                {
                    "$set": {
                        "avatar_url": None,
                        "avatar_thumbnail_url": None,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            logger.info(f"Avatar deleted for user {user.id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting avatar: {e}")
            return False
    
    async def upload_file(
        self,
        user: UserInDB,
        file: UploadFile,
        public: bool = False,
        tags: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        Subir archivo general
        
        Args:
            user: Usuario que sube el archivo
            file: Archivo a subir
            public: Si el archivo debe ser público
            tags: Etiquetas para el archivo
        
        Returns:
            Información del archivo subido
        """
        try:
            # Subir archivo
            result = storage_client.upload_file(
                file=file,
                prefix=f"users/{user.id}/",
                public=public
            )
            
            # Guardar metadatos en base de datos
            file_doc = {
                "_id": ObjectId(),
                "user_id": ObjectId(user.id),
                "filename": result["filename"],
                "original_name": result["original_name"],
                "content_type": result["content_type"],
                "size": result["size"],
                "path": result["path"],
                "url": result["url"],
                "bucket": result["bucket"],
                "public": public,
                "tags": tags or [],
                "uploaded_at": datetime.utcnow(),
                "last_accessed": datetime.utcnow()
            }
            
            await self.db.files.insert_one(file_doc)
            
            # Actualizar storage usado por el usuario
            await self.db.users.update_one(
                {"_id": ObjectId(user.id)},
                {
                    "$inc": {"storage_used": result["size"]},
                    "$set": {"updated_at": datetime.utcnow()}
                }
            )
            
            logger.info(f"File uploaded by user {user.id}: {result['filename']}")
            
            return {
                "file_id": str(file_doc["_id"]),
                **result
            }
            
        except Exception as e:
            logger.error(f"Error uploading file: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error uploading file: {str(e)}"
            )
    
    async def get_user_files(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 50,
        file_type: Optional[str] = None
    ) -> list:
        """Obtener archivos de un usuario"""
        query = {"user_id": ObjectId(user_id)}
        
        if file_type:
            query["content_type"] = {"$regex": f"^{file_type}"}
        
        files = await self.db.files.find(query).skip(skip).limit(limit).to_list(limit)
        
        # Convertir ObjectId a strings
        for file in files:
            file["_id"] = str(file["_id"])
            file["user_id"] = str(file["user_id"])
        
        return files
    
    async def delete_file(self, user_id: str, file_id: str) -> bool:
        """Eliminar archivo del usuario"""
        try:
            # Buscar archivo
            file = await self.db.files.find_one({
                "_id": ObjectId(file_id),
                "user_id": ObjectId(user_id)
            })
            
            if not file:
                return False
            
            # Eliminar del storage
            storage_client.delete_file(file["path"])
            
            # Eliminar de la base de datos
            await self.db.files.delete_one({"_id": ObjectId(file_id)})
            
            # Actualizar storage usado
            await self.db.users.update_one(
                {"_id": ObjectId(user_id)},
                {
                    "$inc": {"storage_used": -file["size"]},
                    "$set": {"updated_at": datetime.utcnow()}
                }
            )
            
            logger.info(f"File deleted: {file_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting file: {e}")
            return False