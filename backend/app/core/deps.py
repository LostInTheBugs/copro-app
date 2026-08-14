from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User

security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    token: str = "",
    db: Session = Depends(get_db),
) -> User:
    """Auth par header Bearer, avec fallback ?token=... (liens de téléchargement directs)."""
    raw = credentials.credentials if credentials else (token or "")
    if not raw:
        raise HTTPException(401, detail="Authentification requise")
    payload = decode_access_token(raw)
    if not payload:
        raise HTTPException(401, detail="Token invalide ou expiré")
    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if not user:
        raise HTTPException(401, detail="Utilisateur introuvable")
    user._token_data = payload
    return user


def require_syndic(user: User = Depends(get_current_user)) -> User:
    if user.role != "syndic":
        raise HTTPException(403, detail="Réservé au syndic")
    return user
