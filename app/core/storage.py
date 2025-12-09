import boto3
from botocore.client import Config
from minio import Minio
from minio.error import S3Error
import io
from typing import Optional, BinaryIO, Tuple
from fastapi import UploadFile, HTTPException, status
import uuid
from datetime import datetime, timedelta

from app.config import settings
from app.utils.image_processor import ImageProcessor
from app.utils.logger import logger


class StorageClient:
    """Cliente unificado para S3 y MinIO"""
    
    def __init__(self):
        self.provider = settings.STORAGE_PROVIDER.lower()
        self.bucket = settings.STORAGE_BUCKET
        
        if self.provider == "s3":
            self._init_s3()
        elif self.provider == "minio":
            self._init_minio()
        else:
            raise ValueError(f"Unsupported storage provider: {self.provider}")
        
        self._ensure_bucket()
    
    def _init_s3(self):
        """Inicializar cliente AWS S3"""
        self.client = boto3.client(
            's3',
            endpoint_url=settings.STORAGE_ENDPOINT,
            aws_access_key_id=settings.STORAGE_ACCESS_KEY,
            aws_secret_access_key=settings.STORAGE_SECRET_KEY,
            region_name=settings.STORAGE_REGION,
            config=Config(signature_version='s3v4')
        )
        logger.info("Initialized S3 client")
    
    def _init_minio(self):
        """Inicializar cliente MinIO"""
        endpoint = settings.MINIO_ENDPOINT
        secure = settings.MINIO_SECURE
        
        self.client = Minio(
            endpoint=endpoint,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=secure
        )
        logger.info(f"Initialized MinIO client: {endpoint}")
    
    def _ensure_bucket(self):
        """Asegurar que el bucket exista"""
        try:
            if self.provider == "s3":
                self.client.head_bucket(Bucket=self.bucket)
            else:
                if not self.client.bucket_exists(self.bucket):
                    self.client.make_bucket(self.bucket)
                    logger.info(f"Created bucket: {self.bucket}")
        except Exception as e:
            logger.error(f"Error ensuring bucket: {e}")
            # En desarrollo, crear el bucket si no existe
            if settings.DEBUG:
                self._create_bucket()
    
    def _create_bucket(self):
        """Crear bucket (solo en desarrollo)"""
        try:
            if self.provider == "s3":
                self.client.create_bucket(
                    Bucket=self.bucket,
                    CreateBucketConfiguration={
                        'LocationConstraint': settings.STORAGE_REGION
                    }
                )
            else:
                self.client.make_bucket(self.bucket)
            logger.info(f"Created bucket: {self.bucket}")
        except Exception as e:
            logger.warning(f"Could not create bucket: {e}")
    
    def upload_file(
        self,
        file: UploadFile,
        prefix: str = "",
        public: bool = False
    ) -> dict:
        """
        Subir archivo al storage
        
        Args:
            file: UploadFile de FastAPI
            prefix: Prefijo para la ruta (ej: 'avatars/')
            public: Si el archivo debe ser público
        
        Returns:
            dict con información del archivo subido
        """
        try:
            # Leer contenido
            content = file.file.read()
            
            # Generar nombre único
            file_ext = file.filename.split('.')[-1] if '.' in file.filename else 'bin'
            unique_filename = f"{uuid.uuid4()}.{file_ext}"
            
            # Construir ruta completa
            object_name = f"{prefix}{unique_filename}" if prefix else unique_filename
            
            # Subir al storage
            if self.provider == "s3":
                extra_args = {'ACL': 'public-read'} if public else {}
                self.client.put_object(
                    Bucket=self.bucket,
                    Key=object_name,
                    Body=content,
                    ContentType=file.content_type,
                    **extra_args
                )
                
                # Generar URL
                if public and settings.STORAGE_PUBLIC_URL:
                    url = f"{settings.STORAGE_PUBLIC_URL}/{object_name}"
                else:
                    url = self.client.generate_presigned_url(
                        'get_object',
                        Params={'Bucket': self.bucket, 'Key': object_name},
                        ExpiresIn=3600  # 1 hora
                    )
            else:
                # MinIO
                content_length = len(content)
                self.client.put_object(
                    bucket_name=self.bucket,
                    object_name=object_name,
                    data=io.BytesIO(content),
                    length=content_length,
                    content_type=file.content_type
                )
                
                # URL para MinIO
                if public:
                    url = self.client.presigned_get_object(
                        self.bucket,
                        object_name,
                        expires=timedelta(hours=1)
                    )
                else:
                    url = f"/{self.bucket}/{object_name}"
            
            logger.info(f"File uploaded: {object_name}")
            
            return {
                "filename": unique_filename,
                "original_name": file.filename,
                "content_type": file.content_type,
                "size": len(content),
                "path": object_name,
                "url": url,
                "bucket": self.bucket
            }
            
        except Exception as e:
            logger.error(f"Error uploading file: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error uploading file: {str(e)}"
            )
    
    def delete_file(self, object_name: str) -> bool:
        """Eliminar archivo del storage"""
        try:
            if self.provider == "s3":
                self.client.delete_object(Bucket=self.bucket, Key=object_name)
            else:
                self.client.remove_object(self.bucket, object_name)
            
            logger.info(f"File deleted: {object_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting file: {e}")
            return False
    
    def get_presigned_url(self, object_name: str, expires: int = 3600) -> str:
        """Obtener URL firmada temporal"""
        try:
            if self.provider == "s3":
                return self.client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': self.bucket, 'Key': object_name},
                    ExpiresIn=expires
                )
            else:
                return self.client.presigned_get_object(
                    self.bucket,
                    object_name,
                    expires=timedelta(seconds=expires)
                )
        except Exception as e:
            logger.error(f"Error generating presigned URL: {e}")
            return ""
    
    def download_file(self, object_name: str) -> Tuple[bytes, str]:
        """Descargar archivo del storage"""
        try:
            if self.provider == "s3":
                response = self.client.get_object(Bucket=self.bucket, Key=object_name)
                content = response['Body'].read()
                content_type = response['ContentType']
            else:
                response = self.client.get_object(self.bucket, object_name)
                content = response.read()
                content_type = response.headers.get('content-type', 'application/octet-stream')
            
            return content, content_type
            
        except Exception as e:
            logger.error(f"Error downloading file: {e}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )


# Instancia global del storage
storage_client = StorageClient()