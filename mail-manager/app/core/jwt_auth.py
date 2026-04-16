import jwt
from app.config import config


def verify_jwt(token):
    if not config.JWT_PUBLIC_KEY:
        return None
    try:
        return jwt.decode(
            token,
            config.JWT_PUBLIC_KEY,
            algorithms=[config.JWT_ALGORITHM],
            issuer=config.JWT_ISSUER,
            audience=config.JWT_AUDIENCE,
        )
    except Exception:
        return None
