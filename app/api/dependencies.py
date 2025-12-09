"""
API-specific dependencies
"""

from app.core.dependencies import (
    get_current_user,
    get_current_active_user,
    get_current_admin,
    get_current_superadmin,
    require_role
)

__all__ = [
    "get_current_user",
    "get_current_active_user", 
    "get_current_admin",
    "get_current_superadmin",
    "require_role"
]