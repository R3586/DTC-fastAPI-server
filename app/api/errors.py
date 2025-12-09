"""
Error handling for the API
"""

import traceback
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError, HTTPException
from fastapi.responses import JSONResponse
from starlette import status as http_status

from app.core.exceptions import AppException
from app.core.config import settings
from app.utils.logger import logger


async def app_exception_handler(request: Request, exc: AppException):
    """Handler para excepciones personalizadas de la app"""
    logger.error(
        f"AppException: {exc.message}",
        extra={
            "request_id": getattr(request.state, "request_id", None),
            "status_code": exc.status_code,
            "error": exc.message
        }
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.message,
            "type": exc.__class__.__name__,
            "request_id": getattr(request.state, "request_id", None)
        }
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handler para errores de validación"""
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })
    
    logger.warning(
        f"Validation error: {errors}",
        extra={
            "request_id": getattr(request.state, "request_id", None),
            "errors": errors
        }
    )
    
    return JSONResponse(
        status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation error",
            "details": errors,
            "request_id": getattr(request.state, "request_id", None)
        }
    )


async def http_exception_handler(request: Request, exc: HTTPException):
    """Handler para excepciones HTTP genéricas"""
    logger.error(
        f"HTTPException: {exc.detail}",
        extra={
            "request_id": getattr(request.state, "request_id", None),
            "status_code": exc.status_code,
            "detail": exc.detail
        }
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "request_id": getattr(request.state, "request_id", None)
        }
    )


async def general_exception_handler(request: Request, exc: Exception):
    """Handler para excepciones generales no manejadas"""
    # Obtener traceback
    tb = traceback.format_exc()
    
    logger.error(
        f"Unhandled exception: {str(exc)}",
        extra={
            "request_id": getattr(request.state, "request_id", None),
            "error": str(exc),
            "traceback": tb,
            "method": request.method,
            "url": str(request.url)
        }
    )
    
    # En producción, no mostrar detalles internos
    if settings.DEBUG:
        detail = {
            "error": "Internal server error",
            "detail": str(exc),
            "traceback": tb,
            "request_id": getattr(request.state, "request_id", None)
        }
    else:
        detail = {
            "error": "Internal server error",
            "request_id": getattr(request.state, "request_id", None)
        }
    
    return JSONResponse(
        status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=detail
    )


def setup_exception_handlers(app: FastAPI):
    """Configurar todos los handlers de excepciones"""
    
    # Importar excepciones personalizadas
    from app.core.exceptions import (
        AuthenticationException,
        AuthorizationException,
        UserNotFoundException,
        ResourceNotFoundException,
        ResourceAlreadyExistsException,
        ValidationException,
        FileTooLargeException,
        InvalidFileTypeException,
        DatabaseConnectionException,
        DatabaseOperationException
    )
    
    # Registrar handlers para excepciones personalizadas
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(AuthenticationException, app_exception_handler)
    app.add_exception_handler(AuthorizationException, app_exception_handler)
    app.add_exception_handler(UserNotFoundException, app_exception_handler)
    app.add_exception_handler(ResourceNotFoundException, app_exception_handler)
    app.add_exception_handler(ResourceAlreadyExistsException, app_exception_handler)
    app.add_exception_handler(ValidationException, app_exception_handler)
    app.add_exception_handler(FileTooLargeException, app_exception_handler)
    app.add_exception_handler(InvalidFileTypeException, app_exception_handler)
    app.add_exception_handler(DatabaseConnectionException, app_exception_handler)
    app.add_exception_handler(DatabaseOperationException, app_exception_handler)
    
    # Handlers estándar
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
    
    logger.info("Exception handlers configured")