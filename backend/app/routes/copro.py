from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user, require_syndic
from app.models.user import User
from app.models.copropriete import Copropriete
from app.schemas import CoproOut, CoproUpdate

router = APIRouter(prefix="/api/copro", tags=["copro"])


def get_or_create_copro(db: Session, user: User) -> Copropriete:
    copro = db.query(Copropriete).first()
    if not copro:
        copro = Copropriete(nom="Ma copropriété")
        db.add(copro)
        db.commit()
        db.refresh(copro)
    if not user.copropriete_id:
        user.copropriete_id = copro.id
        db.commit()
    return copro


@router.get("", response_model=CoproOut)
def get_copro(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return get_or_create_copro(db, user)


@router.put("", response_model=CoproOut)
def update_copro(
    data: CoproUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_syndic),
):
    copro = get_or_create_copro(db, user)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(copro, field, value)
    db.commit()
    db.refresh(copro)
    return copro
