from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user, require_syndic
from app.models.user import User
from app.models.lot import Lot
from app.models.personne import Personne
from app.models.appel import AppelFonds, AppelLot
from app.models.mouvement import Mouvement
from app.schemas import LotIn, LotOut, PersonneIn, PersonneOut, LotSolde
from app.routes.copro import get_or_create_copro

router = APIRouter(prefix="/api", tags=["lots"])


# ---------- Personnes ----------
@router.get("/personnes", response_model=list[PersonneOut])
def list_personnes(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    copro = get_or_create_copro(db, user)
    return db.query(Personne).filter(Personne.copropriete_id == copro.id).order_by(Personne.nom).all()


@router.post("/personnes", response_model=PersonneOut)
def create_personne(data: PersonneIn, db: Session = Depends(get_db), user: User = Depends(require_syndic)):
    copro = get_or_create_copro(db, user)
    p = Personne(copropriete_id=copro.id, **data.model_dump())
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


@router.put("/personnes/{personne_id}", response_model=PersonneOut)
def update_personne(personne_id: int, data: PersonneIn, db: Session = Depends(get_db), user: User = Depends(require_syndic)):
    p = db.query(Personne).filter(Personne.id == personne_id).first()
    if not p:
        raise HTTPException(404, "Personne introuvable")
    for field, value in data.model_dump().items():
        setattr(p, field, value)
    db.commit()
    db.refresh(p)
    return p


@router.delete("/personnes/{personne_id}")
def delete_personne(personne_id: int, db: Session = Depends(get_db), user: User = Depends(require_syndic)):
    p = db.query(Personne).filter(Personne.id == personne_id).first()
    if not p:
        raise HTTPException(404, "Personne introuvable")
    db.delete(p)
    db.commit()
    return {"ok": True}


# ---------- Lots ----------
@router.get("/lots", response_model=list[LotOut])
def list_lots(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    copro = get_or_create_copro(db, user)
    return db.query(Lot).filter(Lot.copropriete_id == copro.id).order_by(Lot.numero).all()


@router.post("/lots", response_model=LotOut)
def create_lot(data: LotIn, db: Session = Depends(get_db), user: User = Depends(require_syndic)):
    copro = get_or_create_copro(db, user)
    lot = Lot(copropriete_id=copro.id, **data.model_dump())
    db.add(lot)
    db.commit()
    db.refresh(lot)
    return lot


@router.put("/lots/{lot_id}", response_model=LotOut)
def update_lot(lot_id: int, data: LotIn, db: Session = Depends(get_db), user: User = Depends(require_syndic)):
    lot = db.query(Lot).filter(Lot.id == lot_id).first()
    if not lot:
        raise HTTPException(404, "Lot introuvable")
    for field, value in data.model_dump().items():
        setattr(lot, field, value)
    db.commit()
    db.refresh(lot)
    return lot


@router.delete("/lots/{lot_id}")
def delete_lot(lot_id: int, db: Session = Depends(get_db), user: User = Depends(require_syndic)):
    lot = db.query(Lot).filter(Lot.id == lot_id).first()
    if not lot:
        raise HTTPException(404, "Lot introuvable")
    db.delete(lot)
    db.commit()
    return {"ok": True}


# ---------- Soldes par lot (état daté) ----------
@router.get("/lots/soldes", response_model=list[LotSolde])
def lots_soldes(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    copro = get_or_create_copro(db, user)
    lots = db.query(Lot).filter(Lot.copropriete_id == copro.id).all()
    result = []
    for lot in lots:
        appels_charges = sum(a.montant_charges for a in db.query(AppelLot).filter(AppelLot.lot_id == lot.id).all())
        appels_fonds = sum(a.montant_fonds_travaux for a in db.query(AppelLot).filter(AppelLot.lot_id == lot.id).all())
        encaisse = sum(
            m.montant for m in db.query(Mouvement).filter(
                Mouvement.lot_id == lot.id, Mouvement.type == "encaissement"
            ).all()
        )
        result.append(LotSolde(
            lot=lot,
            proprietaire=lot.proprietaire,
            occupant=lot.occupant,
            total_appels=round(appels_charges, 2),
            total_appels_fonds=round(appels_fonds, 2),
            total_encaisse=round(encaisse, 2),
            solde=round(appels_charges + appels_fonds - encaisse, 2),
        ))
    return result
