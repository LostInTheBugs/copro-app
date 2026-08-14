from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import hash_password, verify_password, create_access_token
from app.core.deps import get_current_user, require_syndic
from app.models.user import User, UserCopro
from app.models.copropriete import Copropriete
from app.schemas import RegisterRequest, LoginRequest, TokenResponse, UserOut, UserCreate, CoproCreate

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _copro_principale(db: Session, user: User) -> int | None:
    """Id de la copropriété principale du user (liaison), sinon None."""
    lien = (db.query(UserCopro).filter(UserCopro.user_id == user.id)
            .order_by(UserCopro.principale.desc(), UserCopro.id).first())
    return lien.copropriete_id if lien else None


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
    return TokenResponse(access_token=create_access_token(user.id, _copro_principale(db, user)))


@router.get("/coproprietes")
def mes_coproprietes(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Liste des copropriétés accessibles + la copro active du token."""
    liens = (db.query(UserCopro).filter(UserCopro.user_id == user.id)
             .order_by(UserCopro.principale.desc(), UserCopro.id).all())
    active = (getattr(user, "_token_data", None) or {}).get("copro_id")
    out = []
    for lien in liens:
        copro = db.query(Copropriete).filter(Copropriete.id == lien.copropriete_id).first()
        if not copro:
            continue
        out.append({
            "id": copro.id,
            "nom": copro.nom,
            "ville": copro.ville or "",
            "principale": bool(lien.principale),
            "active": active is not None and int(active) == copro.id,
        })
    # Fallback : token sans copro_id → active = première liaison
    if active is None and out:
        out[0]["active"] = True
    return out


@router.post("/switch-copro/{copro_id}", response_model=TokenResponse)
def switch_copro(copro_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Bascule la copropriété active du user (nouveau token avec copro_id)."""
    lien = (db.query(UserCopro)
            .filter(UserCopro.user_id == user.id, UserCopro.copropriete_id == copro_id)
            .first())
    if not lien:
        raise HTTPException(403, "Accès refusé à cette copropriété")
    return TokenResponse(access_token=create_access_token(user.id, copro_id))


@router.post("/coproprietes", response_model=TokenResponse)
def creer_copropriete(data: CoproCreate, db: Session = Depends(get_db), user: User = Depends(require_syndic)):
    """Crée une nouvelle copropriété pour le syndic (devient la copro active)."""
    copro = Copropriete(
        nom=data.nom, adresse=data.adresse, ville=data.ville, code_postal=data.code_postal,
        annee_construction=data.annee_construction,
    )
    db.add(copro)
    db.commit()
    db.refresh(copro)
    db.add(UserCopro(user_id=user.id, copropriete_id=copro.id, principale=True))
    db.commit()
    return TokenResponse(access_token=create_access_token(user.id, copro.id))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.post("/users", response_model=UserOut)
def create_user(req: UserCreate, db: Session = Depends(get_db), user: User = Depends(require_syndic)):
    if db.query(User).filter(User.email == req.email.lower().strip()).first():
        raise HTTPException(400, "Cet email est déjà utilisé")
    # Le compte créé est lié à la copropriété active du syndic
    from app.routes.copro import get_or_create_copro
    copro = get_or_create_copro(db, user)
    new_user = User(
        email=req.email.lower().strip(),
        password_hash=hash_password(req.password),
        nom=req.nom.strip(),
        role=req.role,
        copropriete_id=copro.id,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    db.add(UserCopro(user_id=new_user.id, copropriete_id=copro.id, principale=True))
    db.commit()
    return new_user


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
