"""
Logging configuration for the application
"""

import logging
import sys
from typing import Any, Dict
from datetime import datetime

from fastapi import Path

from app.core.config import settings


class JSONFormatter(logging.Formatter):
    """Formateador de logs en JSON"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Agregar extras si existen
        if hasattr(record, 'extra'):
            log_data.update(record.extra)
        
        # Agregar excepción si existe
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # En desarrollo, formato más legible
        if settings.DEBUG:
            return f"{log_data['timestamp']} | {log_data['level']:5} | {log_data['module']:5} : {log_data['function']:5} : {log_data['line']} - {log_data['message']}"
        
        # En producción, retornar como string (podrías usar json.dumps aquí)
        return str(log_data)

def setup_logger():
    """Configurar el logger de la aplicación"""
    
    # Crear logger
    logger = logging.getLogger("dtc_logger")
    logger.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)
    
    # Evitar propagación al logger root
    logger.propagate = False
    
    # Remover handlers existentes
    logger.handlers.clear()
    
    # Handler para consola
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)
    console_handler.setFormatter(JSONFormatter())
    logger.addHandler(console_handler)
    
    # Handler para archivo (solo en producción)
    if not settings.DEBUG:
        try:
            # Crear directorio logs si no existe
            log_dir = Path("logs")
            log_dir.mkdir(exist_ok=True)
            
            file_handler = logging.FileHandler("logs/app.log")
            file_handler.setLevel(logging.INFO)
            file_handler.setFormatter(JSONFormatter())
            logger.addHandler(file_handler)
            logger.info("File logging enabled")
        except Exception as e:
            # Solo mostrar warning en consola, no fallar
            logger.warning(f"Could not setup file logging: {e}")
    
    return logger


# Logger global
logger = setup_logger()