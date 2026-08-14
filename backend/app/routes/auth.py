from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import hash_password, verify_password, create_access_token
from app.core.deps import get_current_user, require_syndic
from app.models.user import User
from app.schemas import RegisterRequest, LoginRequest, TokenResponse, UserOut, UserCreate

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    """Création du premier compte (syndic). Fermé dès qu'un utilisateur existe."""
    if db.query(User).count() > 0:
        raise HTTPException(403, "Inscription fermée : un compte existe déjà")
    user = User(
        email=req.email.lower().strip(),
        password_hash=hash_password(req.password),
        nom=req.nom.strip(),
        role="syndic",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return TokenResponse(access_token=create_access_token(user.id))


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email.lower().strip()).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(401, "Email ou mot de passe incorrect")
    return TokenResponse(access_token=create_access_token(user.id))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.post("/users", response_model=UserOut)
def create_user(req: UserCreate, db: Session = Depends(get_db), _: User = Depends(require_syndic)):
    if db.query(User).filter(User.email == req.email.lower().strip()).first():
        raise HTTPException(400, "Cet email est déjà utilisé")
    user = User(
        email=req.email.lower().strip(),
        password_hash=hash_password(req.password),
        nom=req.nom.strip(),
        role=req.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/users", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), _: User = Depends(require_syndic)):
    return db.query(User).order_by(User.nom).all()


@router.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), current: User = Depends(require_syndic)):
    if user_id == current.id:
        raise HTTPException(400, "Impossible de supprimer son propre compte")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "Utilisateur introuvable")
    db.delete(user)
    db.commit()
    return {"ok": True}
