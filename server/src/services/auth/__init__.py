from .models import AuthService
from .local_impl import LocalAuthService
from .cloud_otp_impl import CloudOtpAuthService
from .cloud_magic_link_impl import CloudMagicLinkAuthService

_service = LocalAuthService()

def get_auth_service() -> AuthService:
    """Return the configured AuthService. Currently defaults to LocalAuthService."""
    return _service
