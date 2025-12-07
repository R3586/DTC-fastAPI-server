from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional
import asyncio

from app.core.config import settings

class Database:
    client: Optional[AsyncIOMotorClient] = None
    db = None
    
    async def connect(self):
        """Conectar a MongoDB"""
        self.client = AsyncIOMotorClient(settings.MONGODB_URL)
        self.db = self.client[settings.MONGODB_DB_NAME]
        
        # Crear índices
        await self.create_indexes()
        print("✅ Connected to MongoDB")
    
    async def create_indexes(self):
        """Crear índices necesarios"""
        # Usuarios
        await self.db.users.create_index("email", unique=True)
        await self.db.users.create_index("username", unique=True, sparse=True)
        await self.db.users.create_index("created_at")
        await self.db.users.create_index("role")
        
        # Sesiones
        await self.db.sessions.create_index("user_id")
        await self.db.sessions.create_index("session_token", unique=True)
        await self.db.sessions.create_index("refresh_token", unique=True)
        await self.db.sessions.create_index("expires_at", expireAfterSeconds=0)
        await self.db.sessions.create_index([("user_id", 1), ("last_active", -1)])
        
        # Blacklist
        await self.db.token_blacklist.create_index("token", unique=True)
        await self.db.token_blacklist.create_index("expires_at", expireAfterSeconds=0)
        await self.db.token_blacklist.create_index("user_id")
    
    async def disconnect(self):
        """Desconectar de MongoDB"""
        if self.client:
            self.client.close()
            print("❌ Disconnected from MongoDB")

# Instancia global
database = Database()

async def get_database():
    """Dependency para obtener la base de datos"""
    if database.db is None:
        await database.connect()
    return database.db