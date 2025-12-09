"""
Custom exceptions for the application
"""

from fastapi import HTTPException as FastAPIHTTPException
from starlette import status as http_status


class AppException(FastAPIHTTPException):
    """Base exception for the application"""
    def __init__(self, message: str, status_code: int = http_status.HTTP_500_INTERNAL_SERVER_ERROR):
        super().__init__(status_code=status_code, detail=message)
        self.message = message


# Authentication exceptions
class AuthenticationException(AppException):
    """Base authentication exception"""
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, http_status.HTTP_401_UNAUTHORIZED)


class InvalidCredentialsException(AuthenticationException):
    """Invalid username or password"""
    def __init__(self, message: str = "Invalid credentials"):
        super().__init__(message)


class TokenExpiredException(AuthenticationException):
    """JWT token has expired"""
    def __init__(self, message: str = "Token has expired"):
        super().__init__(message)


class TokenInvalidException(AuthenticationException):
    """JWT token is invalid"""
    def __init__(self, message: str = "Invalid token"):
        super().__init__(message)


# Authorization exceptions
class AuthorizationException(AppException):
    """Base authorization exception"""
    def __init__(self, message: str = "Authorization failed"):
        super().__init__(message, http_status.HTTP_403_FORBIDDEN)


class InsufficientPermissionsException(AuthorizationException):
    """User doesn't have required permissions"""
    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(message)


class UserNotFoundException(AppException):
    """User not found"""
    def __init__(self, message: str = "User not found"):
        super().__init__(message, http_status.HTTP_404_NOT_FOUND)


# Resource exceptions
class ResourceNotFoundException(AppException):
    """Resource not found"""
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, http_status.HTTP_404_NOT_FOUND)


class ResourceAlreadyExistsException(AppException):
    """Resource already exists"""
    def __init__(self, message: str = "Resource already exists"):
        super().__init__(message, http_status.HTTP_409_CONFLICT)


class ValidationException(AppException):
    """Validation error"""
    def __init__(self, message: str = "Validation error"):
        super().__init__(message, http_status.HTTP_400_BAD_REQUEST)


# File handling exceptions
class FileTooLargeException(AppException):
    """File is too large"""
    def __init__(self, message: str = "File is too large"):
        super().__init__(message, http_status.HTTP_400_BAD_REQUEST)


class InvalidFileTypeException(AppException):
    """Invalid file type"""
    def __init__(self, message: str = "Invalid file type"):
        super().__init__(message, http_status.HTTP_400_BAD_REQUEST)


# Database exceptions
class DatabaseConnectionException(AppException):
    """Database connection error"""
    def __init__(self, message: str = "Database connection error"):
        super().__init__(message, http_status.HTTP_503_SERVICE_UNAVAILABLE)


class DatabaseOperationException(AppException):
    """Database operation error"""
    def __init__(self, message: str = "Database operation error"):
        super().__init__(message, http_status.HTTP_500_INTERNAL_SERVER_ERROR)