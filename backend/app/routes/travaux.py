from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user, require_syndic
from app.models.user import User
from app.models.travaux import Travaux
from app.routes.copro import get_or_create_copro
from app.schemas import TravauxIn, TravauxOut

router = APIRouter(prefix="/api/travaux", tags=["travaux"])

_CATEGORIES = {
    "toiture": "Toiture / couverture",
    "facade": "Façade / ravalement",
    "chauffage": "Chauffage / climatisation",
    "electricite": "Électricité / parties communes",
    "plomberie": "Plomberie / sanitaire",
    "ascenseur": "Ascenseur",
    "securite": "Sécurité / incendie",
    "communs": "Parties communes",
    "autres": "Autres",
}

_STATUTS = {"planifie": "Planifié", "en_cours": "En cours", "realise": "Réalisé"}


@router.get("", response_model=list[TravauxOut])
def liste(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    copro = get_or_create_copro(db, user)
    return db.query(Travaux).filter(Travaux.copropriete_id == copro.id).order_by(Travaux.annee, Travaux.id).all()


@router.post("", response_model=TravauxOut)
def creer(data: TravauxIn, db: Session = Depends(get_db), user: User = Depends(require_syndic)):
    copro = get_or_create_copro(db, user)
    t = Travaux(copropriete_id=copro.id, **data.model_dump())
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


@router.put("/{travaux_id}", response_model=TravauxOut)
def modifier(travaux_id: int, data: TravauxIn, db: Session = Depends(get_db), user: User = Depends(require_syndic)):
    t = db.query(Travaux).filter(Travaux.id == travaux_id).first()
    if not t:
        raise HTTPException(404, "Travaux introuvables")
    for k, v in data.model_dump().items():
        setattr(t, k, v)
    db.commit()
    db.refresh(t)
    return t


@router.delete("/{travaux_id}")
def supprimer(travaux_id: int, db: Session = Depends(get_db), user: User = Depends(require_syndic)):
    t = db.query(Travaux).filter(Travaux.id == travaux_id).first()
    if not t:
        raise HTTPException(404, "Travaux introuvables")
    db.delete(t)
    db.commit()
    return {"ok": True}


@router.get("/categories")
def categories():
    return _CATEGORIES


@router.get("/statuts")
def statuts():
    return _STATUTS
