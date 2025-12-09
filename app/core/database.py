"""
Database connection and utilities
"""

from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional


from .config import settings
from .exceptions import DatabaseConnectionException
from app.utils.logger import logger

class Database:
    """Manejador de conexión a MongoDB"""
    
    client: Optional[AsyncIOMotorClient] = None
    db = None
    
    async def connect(self):
        """Conectar a MongoDB"""
        try:
            self.client = AsyncIOMotorClient(
                settings.MONGODB_URL,
                maxPoolSize=settings.MONGODB_MAX_POOL_SIZE,
                minPoolSize=settings.MONGODB_MIN_POOL_SIZE
            )
            self.db = self.client[settings.MONGODB_DB_NAME]
            
            # Crear índices
            await self.create_indexes()
            
            # Verificar conexión
            await self.client.admin.command('ping')
            
            logger.info("✅ Connected to MongoDB")
            
        except Exception as e:
            logger.info(f"❌ Failed to connect to MongoDB: {e}")
            raise DatabaseConnectionException(f"Failed to connect to MongoDB: {e}")
    
    async def create_indexes(self):
        """Crear índices necesarios"""
        try:
            # Usuarios
            await self.db.users.create_index("email", unique=True)
            await self.db.users.create_index("username", unique=True, sparse=True)
            await self.db.users.create_index("created_at")
            await self.db.users.create_index("role")
            await self.db.users.create_index("is_active")
            
            # Sesiones
            await self.db.sessions.create_index("user_id")
            await self.db.sessions.create_index("session_token", unique=True)
            await self.db.sessions.create_index("refresh_token", unique=True)
            await self.db.sessions.create_index("expires_at", expireAfterSeconds=0)
            await self.db.sessions.create_index([("user_id", 1), ("last_active", -1)])
            
            # Blacklist de tokens
            await self.db.token_blacklist.create_index("token", unique=True)
            await self.db.token_blacklist.create_index("expires_at", expireAfterSeconds=0)
            await self.db.token_blacklist.create_index("user_id")
            
            # Archivos
            await self.db.files.create_index("user_id")
            await self.db.files.create_index("uploaded_at")
            await self.db.files.create_index("content_type")
            await self.db.files.create_index("tags")
            await self.db.files.create_index([("user_id", 1), ("uploaded_at", -1)])
            
            # Logs
            await self.db.logs.create_index("timestamp")
            await self.db.logs.create_index("level")
            
            logger.info("✅ Database indexes created")
            
        except Exception as e:
            logger.info(f"⚠️ Warning: Could not create all indexes: {e}")
    
    async def disconnect(self):
        """Desconectar de MongoDB"""
        if self.client:
            self.client.close()
            logger.info("❌ Disconnected from MongoDB")


# Instancia global de la base de datos
database = Database()


async def get_database():
    """
    Dependency para obtener la base de datos en las rutas
    
    Usage:
        @app.get("/items")
        async def read_items(db = Depends(get_database)):
            items = await db.collection.find().to_list(100)
            return items
    """
    if database.db is None:
        await database.connect()
    return database.db


# Excepción personalizada para errores de base de datos
class DatabaseConnectionException(Exception):
    """Excepción para errores de conexión a la base de datos"""
    pass