#!/usr/bin/env python3
"""
Script de inicialización de la base de datos
"""

import asyncio
import sys
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import database
from app.core.config import settings
from app.utils.logger import logger


async def init_database():
    """Inicializar la base de datos con datos de prueba"""
    
    logger.info("🔄 Inicializando base de datos...")
    
    try:
        # Conectar a la base de datos
        await database.connect()
        db = database.db
        
        # Verificar si ya existen datos
        user_count = await db.users.count_documents({})
        
        if user_count > 0:
            logger.info("✅ Base de datos ya inicializada")
            return
        
        # Crear usuario administrador de prueba
        from app.core.security import get_password_hash
        from datetime import datetime
        
        admin_user = {
            "_id": "507f1f77bcf86cd799439011",
            "email": "admin@xstv.com",
            "username": "admin",
            "full_name": "Administrador",
            "hashed_password": get_password_hash("Admin123!"),
            "role": "superadmin",
            "status": "active",
            "is_active": True,
            "email_verified": True,
            "avatar_url": None,
            "avatar_thumbnail_url": None,
            "bio": "Usuario administrador del sistema",
            "website": "https://xstv.com",
            "location": "Ciudad de México",
            "marketing_emails": False,
            "two_factor_enabled": False,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "last_login": None,
            "login_count": 0,
            "storage_used": 0
        }
        
        await db.users.insert_one(admin_user)
        
        # Crear usuario normal de prueba
        normal_user = {
            "_id": "607f1f77bcf86cd799439012",
            "email": "user@xstv.com",
            "username": "usuario",
            "full_name": "Usuario de Prueba",
            "hashed_password": get_password_hash("User123!"),
            "role": "user",
            "status": "active",
            "is_active": True,
            "email_verified": True,
            "avatar_url": None,
            "avatar_thumbnail_url": None,
            "bio": "Usuario normal del sistema",
            "website": None,
            "location": None,
            "marketing_emails": True,
            "two_factor_enabled": False,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "last_login": None,
            "login_count": 0,
            "storage_used": 0
        }
        
        await db.users.insert_one(normal_user)
        
        logger.info("✅ Base de datos inicializada exitosamente")
        logger.info("👤 Usuarios creados:")
        logger.info(f"   - admin@xstv.com / Admin123! (superadmin)")
        logger.info(f"   - user@xstv.com / User123! (user)")
        
    except Exception as e:
        logger.error(f"❌ Error inicializando base de datos: {e}")
        raise
    finally:
        await database.disconnect()


if __name__ == "__main__":
    asyncio.run(init_database())