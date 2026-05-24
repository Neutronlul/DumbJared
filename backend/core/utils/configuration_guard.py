from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


def require_settings(*setting_names: str, reason: str) -> None:
    """Raise if any required Django settings are missing or falsy."""
    missing = [name for name in setting_names if not getattr(settings, name, None)]
    if missing:
        msg = (
            f"Missing required environment configuration for {reason}: "
            f"{', '.join(missing)}"
        )
        raise ImproperlyConfigured(msg)
