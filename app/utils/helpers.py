"""
Helper functions for the application
"""

import re
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from urllib.parse import urlparse


def is_valid_email(email: str) -> bool:
    """Validar formato de email"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def is_valid_url(url: str) -> bool:
    """Validar formato de URL"""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False


def format_bytes(size: int) -> str:
    """Formatear bytes a string legible"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} PB"


def parse_timedelta(delta_str: str) -> Optional[timedelta]:
    """
    Parsear string de timedelta
    
    Formatos soportados:
    - "1h" -> 1 hora
    - "30m" -> 30 minutos
    - "2d" -> 2 días
    - "1w" -> 1 semana
    """
    if not delta_str:
        return None
    
    # Expresión regular para capturar número y unidad
    pattern = r'^(\d+)([smhdw])$'
    match = re.match(pattern, delta_str.lower())
    
    if not match:
        return None
    
    value = int(match.group(1))
    unit = match.group(2)
    
    if unit == 's':
        return timedelta(seconds=value)
    elif unit == 'm':
        return timedelta(minutes=value)
    elif unit == 'h':
        return timedelta(hours=value)
    elif unit == 'd':
        return timedelta(days=value)
    elif unit == 'w':
        return timedelta(weeks=value)
    
    return None


def safe_get(dictionary: Dict, *keys, default: Any = None) -> Any:
    """
    Obtener valor de diccionario de forma segura
    
    Ejemplo:
        safe_get(data, 'user', 'profile', 'name', default='Unknown')
    """
    current = dictionary
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default
    return current


def chunk_list(lst: List, chunk_size: int) -> List[List]:
    """Dividir lista en chunks del tamaño especificado"""
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


def generate_filename(original_name: str, prefix: str = "", suffix: str = "") -> str:
    """
    Generar nombre de archivo único
    
    Args:
        original_name: Nombre original del archivo
        prefix: Prefijo opcional
        suffix: Sufijo opcional (antes de la extensión)
    """
    import uuid
    from pathlib import Path
    
    path = Path(original_name)
    extension = path.suffix.lower()
    stem = path.stem
    
    # Limpiar nombre base
    clean_stem = re.sub(r'[^\w\-_]', '_', stem)
    
    # Generar nombre único
    unique_id = uuid.uuid4().hex[:8]
    
    # Construir nuevo nombre
    parts = []
    if prefix:
        parts.append(prefix)
    
    parts.append(clean_stem)
    
    if suffix:
        parts.append(suffix)
    
    parts.append(unique_id)
    
    new_stem = "_".join(parts)
    
    return f"{new_stem}{extension}"


def get_client_ip(request) -> Optional[str]:
    """Obtener IP real del cliente"""
    if hasattr(request, 'client') and request.client:
        return request.client.host
    
    # Intentar obtener de headers comunes de proxy
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    return None


def mask_email(email: str) -> str:
    """Enmascarar email para mostrar parcialmente"""
    if "@" not in email:
        return email
    
    local, domain = email.split("@")
    
    if len(local) <= 2:
        masked_local = local[0] + "***"
    else:
        masked_local = local[0] + "***" + local[-1]
    
    return f"{masked_local}@{domain}"


def mask_credit_card(card_number: str) -> str:
    """Enmascarar número de tarjeta de crédito"""
    if len(card_number) < 4:
        return "****"
    
    return "**** **** **** " + card_number[-4:]


def calculate_age(birth_date: datetime) -> int:
    """Calcular edad a partir de fecha de nacimiento"""
    today = datetime.utcnow().date()
    
    # Si birth_date es datetime, convertir a date
    if isinstance(birth_date, datetime):
        birth_date = birth_date.date()
    
    age = today.year - birth_date.year
    
    # Ajustar si aún no ha pasado el cumpleaños este año
    if (today.month, today.day) < (birth_date.month, birth_date.day):
        age -= 1
    
    return age