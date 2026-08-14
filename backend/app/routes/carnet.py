from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user, require_syndic
from app.models.user import User
from app.models.carnet import Entretien
from app.routes.copro import get_or_create_copro
from app.schemas import EntretienIn, EntretienOut

router = APIRouter(prefix="/api/carnet", tags=["carnet"])


@router.get("", response_model=list[EntretienOut])
def list_entretiens(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    copro = get_or_create_copro(db, user)
    return db.query(Entretien).filter(Entretien.copropriete_id == copro.id).order_by(Entretien.date.desc()).all()


@router.post("", response_model=EntretienOut)
def create_entretien(data: EntretienIn, db: Session = Depends(get_db), user: User = Depends(require_syndic)):
    copro = get_or_create_copro(db, user)
    e = Entretien(copropriete_id=copro.id, **data.model_dump())
    db.add(e)
    db.commit()
    db.refresh(e)
    return e


@router.put("/{entretien_id}", response_model=EntretienOut)
def update_entretien(entretien_id: int, data: EntretienIn, db: Session = Depends(get_db), user: User = Depends(require_syndic)):
    e = db.query(Entretien).filter(Entretien.id == entretien_id).first()
    if not e:
        raise HTTPException(404, "Intervention introuvable")
    for field, value in data.model_dump().items():
        setattr(e, field, value)
    db.commit()
    db.refresh(e)
    return e


@router.delete("/{entretien_id}")
def delete_entretien(entretien_id: int, db: Session = Depends(get_db), user: User = Depends(require_syndic)):
    e = db.query(Entretien).filter(Entretien.id == entretien_id).first()
    if not e:
        raise HTTPException(404, "Intervention introuvable")
    db.delete(e)
    db.commit()
    return {"ok": True}
