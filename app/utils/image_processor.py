from PIL import Image
import io
from fastapi import UploadFile, HTTPException, status
from typing import Tuple, Optional
import imghdr
from app.config import settings
from app.utils.logger import logger


class ImageProcessor:
    """Procesador de imágenes para avatares"""
    
    @staticmethod
    def validate_image(file: UploadFile) -> Tuple[bool, str]:
        """Validar archivo de imagen"""
        # Verificar tamaño máximo
        file.file.seek(0, 2)  # Ir al final
        file_size = file.file.tell()
        file.file.seek(0)  # Volver al inicio
        
        max_size = settings.AVATAR_MAX_SIZE_MB * 1024 * 1024
        if file_size > max_size:
            return False, f"File too large. Max size: {settings.AVATAR_MAX_SIZE_MB}MB"
        
        # Verificar tipo MIME
        if file.content_type not in settings.AVATAR_ALLOWED_TYPES:
            return False, f"Invalid file type. Allowed: {', '.join(settings.AVATAR_ALLOWED_TYPES)}"
        
        # Verificar que realmente sea una imagen
        try:
            content = file.file.read(512)  # Leer primeros bytes para detección
            file.file.seek(0)
            
            image_type = imghdr.what(None, content)
            if not image_type or image_type not in ['jpeg', 'png', 'webp']:
                return False, "Invalid image file"
        except Exception:
            return False, "Could not read image file"
        
        return True, ""
    
    @staticmethod
    def process_avatar(
        file: UploadFile,
        resize: bool = True,
        crop_to_square: bool = True,
        create_thumbnail: bool = True
    ) -> dict:
        """
        Procesar imagen de avatar
        
        Returns:
            dict con imágenes procesadas (original, resized, thumbnail)
        """
        try:
            # Leer imagen
            image_bytes = file.file.read()
            image = Image.open(io.BytesIO(image_bytes))
            
            # Convertir a RGB si es RGBA
            if image.mode in ('RGBA', 'LA'):
                background = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'RGBA':
                    background.paste(image, mask=image.split()[-1])
                else:
                    background.paste(image, mask=image.getchannel('A'))
                image = background
            
            results = {
                "original": {
                    "image": image,
                    "format": image.format,
                    "size": image.size
                }
            }
            
            # Redimensionar si es necesario
            if resize:
                resized_image = ImageProcessor._resize_image(
                    image,
                    max_width=settings.AVATAR_MAX_WIDTH,
                    max_height=settings.AVATAR_MAX_HEIGHT
                )
                results["resized"] = {
                    "image": resized_image,
                    "size": resized_image.size
                }
            
            # Recortar a cuadrado si es necesario
            if crop_to_square and results.get("resized"):
                square_image = ImageProcessor._crop_to_square(results["resized"]["image"])
                results["square"] = {
                    "image": square_image,
                    "size": square_image.size
                }
            
            # Crear thumbnail
            if create_thumbnail:
                if results.get("square"):
                    base_image = results["square"]["image"]
                elif results.get("resized"):
                    base_image = results["resized"]["image"]
                else:
                    base_image = image
                
                thumbnail = ImageProcessor._create_thumbnail(
                    base_image,
                    size=settings.AVATAR_THUMBNAIL_SIZE
                )
                results["thumbnail"] = {
                    "image": thumbnail,
                    "size": thumbnail.size
                }
            
            # Convertir a bytes
            for key in results:
                if key != "original":
                    img_obj = results[key]["image"]
                    format = results["original"]["format"] or "JPEG"
                    
                    buffer = io.BytesIO()
                    if format.upper() == "JPEG":
                        img_obj.save(buffer, format="JPEG", quality=85, optimize=True)
                    elif format.upper() == "PNG":
                        img_obj.save(buffer, format="PNG", optimize=True)
                    elif format.upper() == "WEBP":
                        img_obj.save(buffer, format="WEBP", quality=85, method=6)
                    else:
                        img_obj.save(buffer, format="JPEG", quality=85)
                    
                    results[key]["bytes"] = buffer.getvalue()
                    buffer.close()
            
            # También guardar original como bytes
            buffer = io.BytesIO()
            image.save(buffer, format=results["original"]["format"] or "JPEG")
            results["original"]["bytes"] = buffer.getvalue()
            buffer.close()
            
            return results
            
        except Exception as e:
            logger.error(f"Error processing image: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Error processing image: {str(e)}"
            )
    
    @staticmethod
    def _resize_image(image: Image.Image, max_width: int, max_height: int) -> Image.Image:
        """Redimensionar imagen manteniendo aspect ratio"""
        width, height = image.size
        
        # Calcular nuevas dimensiones
        if width > max_width or height > max_height:
            ratio = min(max_width / width, max_height / height)
            new_width = int(width * ratio)
            new_height = int(height * ratio)
            
            return image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        return image
    
    @staticmethod
    def _crop_to_square(image: Image.Image) -> Image.Image:
        """Recortar imagen a cuadrado desde el centro"""
        width, height = image.size
        
        if width == height:
            return image
        
        # Determinar el lado más corto
        min_side = min(width, height)
        
        # Coordenadas para recortar
        left = (width - min_side) // 2
        top = (height - min_side) // 2
        right = left + min_side
        bottom = top + min_side
        
        return image.crop((left, top, right, bottom))
    
    @staticmethod
    def _create_thumbnail(image: Image.Image, size: int) -> Image.Image:
        """Crear thumbnail cuadrado"""
        # Primero asegurar que sea cuadrado
        if image.size[0] != image.size[1]:
            image = ImageProcessor._crop_to_square(image)
        
        # Redimensionar al tamaño del thumbnail
        return image.resize((size, size), Image.Resampling.LANCZOS)
    
    @staticmethod
    def get_image_info(image_bytes: bytes) -> dict:
        """Obtener información de la imagen"""
        try:
            image = Image.open(io.BytesIO(image_bytes))
            return {
                "format": image.format,
                "mode": image.mode,
                "size": image.size,
                "width": image.width,
                "height": image.height
            }
        except Exception as e:
            logger.error(f"Error getting image info: {e}")
            return {}


# Instancia global
image_processor = ImageProcessor()