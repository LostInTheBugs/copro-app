from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user, require_syndic
from app.models.user import User
from app.models.lot import Lot
from app.models.ag import AG, Resolution, Vote
from app.routes.copro import get_or_create_copro
from app.services.country_rules import calculer_statut_resolution, MAJORITES
from app.schemas import AGIn, AGOut, ResolutionIn, ResolutionOut, VoteIn, VoteOut, ResolutionResult

router = APIRouter(prefix="/api", tags=["ag"])


def _resolution_out(db: Session, r: Resolution) -> ResolutionOut:
    lots = db.query(Lot).all()
    resultat = calculer_statut_resolution(r, lots, r.votes)
    return ResolutionOut(
        id=r.id, ag_id=r.ag_id, numero=r.numero, libelle=r.libelle,
        texte=r.texte, majorite=r.majorite, statut=r.statut,
        votes=[VoteOut.model_validate(v) for v in r.votes],
        resultat=ResolutionResult(**resultat),
    )


def _ag_out(db: Session, ag: AG) -> AGOut:
    return AGOut(
        id=ag.id, date=ag.date, type_ag=ag.type_ag, statut=ag.statut,
        lieu=ag.lieu, notes=ag.notes,
        resolutions=[_resolution_out(db, r) for r in sorted(ag.resolutions, key=lambda x: x.numero)],
    )


@router.get("/majorites")
def majorites():
    """Description des majorités légales (module France)."""
    return MAJORITES


@router.get("/ag", response_model=list[AGOut])
def list_ag(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    copro = get_or_create_copro(db, user)
    ags = db.query(AG).filter(AG.copropriete_id == copro.id).order_by(AG.date.desc()).all()
    return [_ag_out(db, ag) for ag in ags]


@router.post("/ag", response_model=AGOut)
def create_ag(data: AGIn, db: Session = Depends(get_db), user: User = Depends(require_syndic)):
    copro = get_or_create_copro(db, user)
    ag = AG(copropriete_id=copro.id, **data.model_dump())
    db.add(ag)
    db.commit()
    db.refresh(ag)
    return _ag_out(db, ag)


@router.put("/ag/{ag_id}", response_model=AGOut)
def update_ag(ag_id: int, data: AGIn, db: Session = Depends(get_db), user: User = Depends(require_syndic)):
    ag = db.query(AG).filter(AG.id == ag_id).first()
    if not ag:
        raise HTTPException(404, "AG introuvable")
    for field, value in data.model_dump().items():
        setattr(ag, field, value)
    db.commit()
    db.refresh(ag)
    return _ag_out(db, ag)


@router.delete("/ag/{ag_id}")
def delete_ag(ag_id: int, db: Session = Depends(get_db), user: User = Depends(require_syndic)):
    ag = db.query(AG).filter(AG.id == ag_id).first()
    if not ag:
        raise HTTPException(404, "AG introuvable")
    db.delete(ag)
    db.commit()
    return {"ok": True}


# ---------- Résolutions ----------
@router.post("/ag/{ag_id}/resolutions", response_model=ResolutionOut)
def add_resolution(ag_id: int, data: ResolutionIn, db: Session = Depends(get_db), user: User = Depends(require_syndic)):
    ag = db.query(AG).filter(AG.id == ag_id).first()
    if not ag:
        raise HTTPException(404, "AG introuvable")
    if data.majorite not in MAJORITES:
        raise HTTPException(400, f"Majorité inconnue : {data.majorite}")
    r = Resolution(ag_id=ag.id, **data.model_dump())
    db.add(r)
    db.commit()
    db.refresh(r)
    return _resolution_out(db, r)


@router.put("/resolutions/{res_id}", response_model=ResolutionOut)
def update_resolution(res_id: int, data: ResolutionIn, db: Session = Depends(get_db), user: User = Depends(require_syndic)):
    r = db.query(Resolution).filter(Resolution.id == res_id).first()
    if not r:
        raise HTTPException(404, "Résolution introuvable")
    for field, value in data.model_dump().items():
        setattr(r, field, value)
    db.commit()
    db.refresh(r)
    return _resolution_out(db, r)


@router.delete("/resolutions/{res_id}")
def delete_resolution(res_id: int, db: Session = Depends(get_db), user: User = Depends(require_syndic)):
    r = db.query(Resolution).filter(Resolution.id == res_id).first()
    if not r:
        raise HTTPException(404, "Résolution introuvable")
    db.delete(r)
    db.commit()
    return {"ok": True}


# ---------- Votes ----------
@router.post("/resolutions/{res_id}/votes", response_model=VoteOut)
def set_vote(res_id: int, data: VoteIn, db: Session = Depends(get_db), user: User = Depends(require_syndic)):
    r = db.query(Resolution).filter(Resolution.id == res_id).first()
    if not r:
        raise HTTPException(404, "Résolution introuvable")
    lot = db.query(Lot).filter(Lot.id == data.lot_id).first()
    if not lot:
        raise HTTPException(404, "Lot introuvable")
    if data.voix not in ("pour", "contre", "abstention", "null"):
        raise HTTPException(400, "Voix invalide")
    vote = db.query(Vote).filter(Vote.resolution_id == res_id, Vote.lot_id == data.lot_id).first()
    if vote:
        vote.voix = data.voix
    else:
        vote = Vote(resolution_id=res_id, lot_id=data.lot_id, voix=data.voix)
        db.add(vote)
    db.commit()
    db.refresh(vote)
    return vote


@router.post("/resolutions/{res_id}/calculer", response_model=ResolutionOut)
def calculer(res_id: int, db: Session = Depends(get_db), user: User = Depends(require_syndic)):
    """Recalcule le statut d'une résolution selon la majorité légale (module FR)."""
    r = db.query(Resolution).filter(Resolution.id == res_id).first()
    if not r:
        raise HTTPException(404, "Résolution introuvable")
    lots = db.query(Lot).all()
    resultat = calculer_statut_resolution(r, lots, r.votes)
    r.statut = resultat["statut"]
    db.commit()
    db.refresh(r)
    return _resolution_out(db, r)
