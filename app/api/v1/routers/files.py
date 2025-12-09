from fastapi import APIRouter, Depends, UploadFile, File, Form, Query, HTTPException, status
from typing import Optional, List
from datetime import datetime, timedelta
from bson import ObjectId
from fastapi.responses import StreamingResponse
import io

from app.core.dependencies import get_current_user
from app.domain.models.user import UserInDB
from app.domain.schemas.file import FileUploadResponse
from app.application.services.file_service import FileService
from app.core.database import get_database
from app.core.storage import storage_client
from app.utils.logger import logger

router = APIRouter(prefix="/files", tags=["files"])


# ========== SUBIR ARCHIVO ==========
@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(..., description="File to upload"),
    public: bool = Form(False, description="Make file publicly accessible"),
    tags: Optional[str] = Form(None, description="Comma-separated tags"),
    current_user: UserInDB = Depends(get_current_user),
    db=Depends(get_database)
):
    """
    Subir un archivo
    
    - **file**: Archivo a subir
    - **public**: Si el archivo debe ser público (default: False)
    - **tags**: Etiquetas separadas por coma para organizar
    """
    file_service = FileService(db)
    
    tags_list = [tag.strip() for tag in tags.split(",")] if tags else []
    
    result = await file_service.upload_file(
        user=current_user,
        file=file,
        public=public,
        tags=tags_list
    )
    
    return FileUploadResponse(
        id=result["file_id"],
        filename=result["filename"],
        original_name=result["original_name"],
        content_type=result["content_type"],
        size=result["size"],
        path=result["path"],
        url=result["url"],
        bucket=result["bucket"],
        public=public,
        uploaded_at=result.get("uploaded_at") or datetime.utcnow()
    )


# ========== LISTAR ARCHIVOS ==========
@router.get("/", response_model=List[dict])
async def get_files(
    skip: int = Query(0, ge=0, description="Número de archivos a saltar"),
    limit: int = Query(50, ge=1, le=100, description="Límite de archivos"),
    file_type: Optional[str] = Query(None, description="Filter by file type (image, video, application, etc)"),
    tag: Optional[str] = Query(None, description="Filter by tag"),
    sort_by: str = Query("uploaded_at", regex="^(uploaded_at|size|original_name)$"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    current_user: UserInDB = Depends(get_current_user),
    db=Depends(get_database)
):
    """
    Obtener archivos del usuario con filtros
    
    Parámetros de filtrado:
    - **file_type**: Tipo MIME principal (image, video, application, text)
    - **tag**: Etiqueta específica
    - **sort_by**: Campo para ordenar
    - **sort_order**: Orden ascendente o descendente
    """
    file_service = FileService(db)
    
    # Obtener archivos
    files = await file_service.get_user_files(
        user_id=current_user.id,
        skip=skip,
        limit=limit,
        file_type=file_type
    )
    
    # Filtrar por tag si se especifica
    if tag:
        files = [f for f in files if tag in f.get("tags", [])]
    
    # Ordenar
    reverse = sort_order == "desc"
    if sort_by == "uploaded_at":
        files.sort(key=lambda x: x.get("uploaded_at") or datetime.min, reverse=reverse)
    elif sort_by == "size":
        files.sort(key=lambda x: x.get("size", 0), reverse=reverse)
    elif sort_by == "original_name":
        files.sort(key=lambda x: x.get("original_name", "").lower(), reverse=reverse)
    
    return files


# ========== OBTENER INFORMACIÓN DE ARCHIVO ==========
@router.get("/{file_id}")
async def get_file(
    file_id: str,
    current_user: UserInDB = Depends(get_current_user),
    db=Depends(get_database)
):
    """
    Obtener información detallada de un archivo
    
    - **file_id**: ID del archivo
    """
    # Buscar archivo
    file = await db.files.find_one({
        "_id": ObjectId(file_id),
        "user_id": ObjectId(current_user.id)
    })
    
    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    # Actualizar último acceso
    await db.files.update_one(
        {"_id": ObjectId(file_id)},
        {"$set": {"last_accessed": datetime.utcnow()}}
    )
    
    # Formatear respuesta
    file["_id"] = str(file["_id"])
    file["user_id"] = str(file["user_id"])
    
    return file


# ========== DESCARGAR ARCHIVO ==========
@router.get("/{file_id}/download")
async def download_file(
    file_id: str,
    current_user: UserInDB = Depends(get_current_user),
    db=Depends(get_database)
):
    """
    Descargar archivo
    
    - **file_id**: ID del archivo
    - Retorna el archivo como stream
    """
    # Buscar archivo
    file = await db.files.find_one({
        "_id": ObjectId(file_id),
        "user_id": ObjectId(current_user.id)
    })
    
    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    # Descargar del storage
    content, content_type = storage_client.download_file(file["path"])
    
    # Actualizar último acceso
    await db.files.update_one(
        {"_id": ObjectId(file_id)},
        {"$set": {"last_accessed": datetime.utcnow()}}
    )
    
    # Retornar como streaming response
    return StreamingResponse(
        io.BytesIO(content),
        media_type=content_type,
        headers={
            "Content-Disposition": f"attachment; filename={file['original_name']}",
            "Content-Length": str(len(content))
        }
    )


# ========== PREVISUALIZAR ARCHIVO ==========
@router.get("/{file_id}/preview")
async def preview_file(
    file_id: str,
    width: Optional[int] = Query(None, ge=50, le=1920),
    height: Optional[int] = Query(None, ge=50, le=1080),
    current_user: UserInDB = Depends(get_current_user),
    db=Depends(get_database)
):
    """
    Previsualizar archivo (solo imágenes por ahora)
    
    - **file_id**: ID del archivo
    - **width**: Ancho deseado (opcional)
    - **height**: Alto deseado (opcional)
    """
    # Buscar archivo
    file = await db.files.find_one({
        "_id": ObjectId(file_id),
        "user_id": ObjectId(current_user.id)
    })
    
    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    # Verificar que sea imagen
    if not file["content_type"].startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Preview only available for images"
        )
    
    # Descargar imagen
    content, content_type = storage_client.download_file(file["path"])
    
    # Procesar imagen si se especifican dimensiones
    if width or height:
        try:
            from PIL import Image
            import io
            
            image = Image.open(io.BytesIO(content))
            
            # Redimensionar manteniendo aspect ratio
            if width and height:
                image = image.resize((width, height), Image.Resampling.LANCZOS)
            elif width:
                ratio = width / image.width
                new_height = int(image.height * ratio)
                image = image.resize((width, new_height), Image.Resampling.LANCZOS)
            elif height:
                ratio = height / image.height
                new_width = int(image.width * ratio)
                image = image.resize((new_width, height), Image.Resampling.LANCZOS)
            
            # Convertir de vuelta a bytes
            buffer = io.BytesIO()
            image_format = content_type.split("/")[-1].upper()
            if image_format == "JPEG":
                image.save(buffer, format="JPEG", quality=85)
            elif image_format == "PNG":
                image.save(buffer, format="PNG")
            else:
                image.save(buffer, format="JPEG", quality=85)
            
            content = buffer.getvalue()
            buffer.close()
            
        except Exception as e:
            logger.warning(f"Could not resize image: {e}")
            # Retornar imagen original si hay error
    
    return StreamingResponse(
        io.BytesIO(content),
        media_type=content_type,
        headers={
            "Content-Disposition": f"inline; filename=preview_{file['original_name']}"
        }
    )


# ========== ELIMINAR ARCHIVO ==========
@router.delete("/{file_id}")
async def delete_file(
    file_id: str,
    current_user: UserInDB = Depends(get_current_user),
    db=Depends(get_database)
):
    """
    Eliminar archivo permanentemente
    
    - **file_id**: ID del archivo a eliminar
    """
    file_service = FileService(db)
    
    success = await file_service.delete_file(current_user.id, file_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found or you don't have permission"
        )
    
    return {"message": "File deleted successfully"}


# ========== COMPARTIR ARCHIVO ==========
@router.post("/{file_id}/share")
async def share_file(
    file_id: str,
    expires_hours: int = Query(24, ge=1, le=168, description="Link expiration in hours"),
    current_user: UserInDB = Depends(get_current_user),
    db=Depends(get_database)
):
    """
    Generar link temporal para compartir archivo
    
    - **file_id**: ID del archivo
    - **expires_hours**: Duración del link en horas (1-168)
    """
    # Buscar archivo
    file = await db.files.find_one({
        "_id": ObjectId(file_id),
        "user_id": ObjectId(current_user.id)
    })
    
    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    # Verificar que el archivo sea público o generar URL firmada
    if file.get("public"):
        share_url = file.get("url")
    else:
        share_url = storage_client.get_presigned_url(
            file["path"],
            expires=expires_hours * 3600
        )
    
    # Registrar acción de compartir
    await db.file_shares.insert_one({
        "file_id": ObjectId(file_id),
        "user_id": ObjectId(current_user.id),
        "share_url": share_url,
        "expires_at": datetime.utcnow() + timedelta(hours=expires_hours),
        "created_at": datetime.utcnow(),
        "access_count": 0
    })
    
    return {
        "file_id": file_id,
        "filename": file["original_name"],
        "share_url": share_url,
        "expires_in_hours": expires_hours,
        "expires_at": datetime.utcnow() + timedelta(hours=expires_hours),
        "public": file.get("public", False)
    }


# ========== ACTUALIZAR METADATOS ==========
@router.patch("/{file_id}/metadata")
async def update_file_metadata(
    file_id: str,
    tags: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    current_user: UserInDB = Depends(get_current_user),
    db=Depends(get_database)
):
    """
    Actualizar metadatos del archivo
    
    - **file_id**: ID del archivo
    - **tags**: Nuevas etiquetas (separadas por coma)
    - **description**: Nueva descripción
    """
    update_data = {}
    
    if tags is not None:
        tags_list = [tag.strip() for tag in tags.split(",")] if tags else []
        update_data["tags"] = tags_list
    
    if description is not None:
        update_data["description"] = description
    
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No data to update"
        )
    
    update_data["updated_at"] = datetime.utcnow()
    
    result = await db.files.update_one(
        {
            "_id": ObjectId(file_id),
            "user_id": ObjectId(current_user.id)
        },
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found or you don't have permission"
        )
    
    return {"message": "File metadata updated successfully"}


# ========== ESTADÍSTICAS DE ARCHIVOS ==========
@router.get("/stats/usage")
async def get_file_stats(
    period: str = Query("month", regex="^(day|week|month|year)$"),
    current_user: UserInDB = Depends(get_current_user),
    db=Depends(get_database)
):
    """
    Obtener estadísticas de uso de archivos
    
    - **period**: Período para las estadísticas (day, week, month, year)
    """
    # Calcular fecha de inicio según el período
    now = datetime.utcnow()
    if period == "day":
        start_date = now - timedelta(days=1)
    elif period == "week":
        start_date = now - timedelta(weeks=1)
    elif period == "month":
        start_date = now - timedelta(days=30)
    else:  # year
        start_date = now - timedelta(days=365)
    
    # Estadísticas de subidas
    upload_stats = await db.files.aggregate([
        {
            "$match": {
                "user_id": ObjectId(current_user.id),
                "uploaded_at": {"$gte": start_date}
            }
        },
        {
            "$group": {
                "_id": {
                    "$dateToString": {
                        "format": "%Y-%m-%d",
                        "date": "$uploaded_at"
                    }
                },
                "count": {"$sum": 1},
                "total_size": {"$sum": "$size"}
            }
        },
        {"$sort": {"_id": 1}}
    ]).to_list(None)
    
    # Archivos por tipo
    type_stats = await db.files.aggregate([
        {
            "$match": {
                "user_id": ObjectId(current_user.id),
                "uploaded_at": {"$gte": start_date}
            }
        },
        {
            "$group": {
                "_id": {"$arrayElemAt": [{"$split": ["$content_type", "/"]}, 0]},
                "count": {"$sum": 1},
                "total_size": {"$sum": "$size"}
            }
        },
        {"$sort": {"total_size": -1}}
    ]).to_list(None)
    
    # Totales
    total_files = await db.files.count_documents({
        "user_id": ObjectId(current_user.id),
        "uploaded_at": {"$gte": start_date}
    })
    
    total_size = await db.files.aggregate([
        {
            "$match": {
                "user_id": ObjectId(current_user.id),
                "uploaded_at": {"$gte": start_date}
            }
        },
        {"$group": {"_id": None, "total": {"$sum": "$size"}}}
    ]).to_list(None)
    
    total_size_mb = round((total_size[0]["total"] if total_size else 0) / (1024 * 1024), 2)
    
    return {
        "period": period,
        "start_date": start_date,
        "end_date": now,
        "total_files": total_files,
        "total_size_mb": total_size_mb,
        "daily_uploads": upload_stats,
        "file_type_distribution": type_stats
    }


# ========== BUSCAR ARCHIVOS ==========
@router.get("/search/{query}")
async def search_files(
    query: str,
    limit: int = Query(20, ge=1, le=100),
    current_user: UserInDB = Depends(get_current_user),
    db=Depends(get_database)
):
    """
    Buscar archivos por nombre o etiquetas
    """
    files = await db.files.find({
        "user_id": ObjectId(current_user.id),
        "$or": [
            {"original_name": {"$regex": query, "$options": "i"}},
            {"tags": {"$regex": query, "$options": "i"}},
            {"description": {"$regex": query, "$options": "i"}}
        ]
    }).limit(limit).to_list(limit)
    
    # Formatear respuesta
    for file in files:
        file["_id"] = str(file["_id"])
        file["user_id"] = str(file["user_id"])
    
    return files