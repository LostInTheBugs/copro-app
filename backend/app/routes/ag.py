from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user, require_syndic
from app.models.user import User
from app.models.lot import Lot
from app.models.personne import Personne
from app.models.ag import AG, Resolution, Vote, AgCreneau, AgCreneauVote
from app.models.invitation import Invitation
from app.models.copropriete import Copropriete
from app.routes.copro import get_or_create_copro
from app.services.country_rules import calculer_statut_resolution, MAJORITES
from app.services.emailer import envoyer_email, convocation_texte, EmailError
from app.schemas import (
    AGIn, AGOut, ResolutionIn, ResolutionOut, VoteIn, VoteOut, ResolutionResult,
    CreneauIn, CreneauOut, CreneauVoteIn, CreneauVoteOut,
    InvitationOut, InvitationsResult,
)

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
        id=ag.id, date=ag.date, heure=ag.heure, type_ag=ag.type_ag, statut=ag.statut,
        lieu=ag.lieu, notes=ag.notes,
        resolutions=[_resolution_out(db, r) for r in sorted(ag.resolutions, key=lambda x: x.numero)],
    )


def _creneau_out(db: Session, c: AgCreneau) -> CreneauOut:
    votes = []
    for v in c.votes:
        lot = db.query(Lot).filter(Lot.id == v.lot_id).first()
        votes.append(CreneauVoteOut(
            id=v.id, lot_id=v.lot_id,
            lot_numero=lot.numero if lot else f"#{v.lot_id}",
            dispo=v.dispo,
        ))
    return CreneauOut(id=c.id, debut=c.debut, fin=c.fin, votes=votes)


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


# ---------- Sondage de dates (type Doodle) ----------
@router.get("/ag/{ag_id}/creneaux", response_model=list[CreneauOut])
def list_creneaux(ag_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ag = db.query(AG).filter(AG.id == ag_id).first()
    if not ag:
        raise HTTPException(404, "AG introuvable")
    creneaux = db.query(AgCreneau).filter(AgCreneau.ag_id == ag.id).order_by(AgCreneau.debut).all()
    return [_creneau_out(db, c) for c in creneaux]


@router.post("/ag/{ag_id}/creneaux", response_model=CreneauOut)
def add_creneau(ag_id: int, data: CreneauIn, db: Session = Depends(get_db), user: User = Depends(require_syndic)):
    ag = db.query(AG).filter(AG.id == ag_id).first()
    if not ag:
        raise HTTPException(404, "AG introuvable")
    if data.fin and data.fin <= data.debut:
        raise HTTPException(400, "La fin doit être après le début")
    c = AgCreneau(ag_id=ag.id, debut=data.debut, fin=data.fin)
    db.add(c)
    db.commit()
    db.refresh(c)
    return _creneau_out(db, c)


@router.delete("/creneaux/{creneau_id}")
def delete_creneau(creneau_id: int, db: Session = Depends(get_db), user: User = Depends(require_syndic)):
    c = db.query(AgCreneau).filter(AgCreneau.id == creneau_id).first()
    if not c:
        raise HTTPException(404, "Créneau introuvable")
    db.delete(c)
    db.commit()
    return {"ok": True}


@router.post("/creneaux/{creneau_id}/votes", response_model=CreneauVoteOut)
def set_creneau_vote(creneau_id: int, data: CreneauVoteIn, db: Session = Depends(get_db), user: User = Depends(require_syndic)):
    """Le syndic saisit la disponibilité d'un lot pour un créneau."""
    c = db.query(AgCreneau).filter(AgCreneau.id == creneau_id).first()
    if not c:
        raise HTTPException(404, "Créneau introuvable")
    lot = db.query(Lot).filter(Lot.id == data.lot_id).first()
    if not lot:
        raise HTTPException(404, "Lot introuvable")
    vote = db.query(AgCreneauVote).filter(
        AgCreneauVote.creneau_id == creneau_id,
        AgCreneauVote.lot_id == data.lot_id,
    ).first()
    if vote:
        vote.dispo = data.dispo
    else:
        vote = AgCreneauVote(creneau_id=creneau_id, lot_id=data.lot_id, dispo=data.dispo)
        db.add(vote)
    db.commit()
    db.refresh(vote)
    lot_row = db.query(Lot).filter(Lot.id == vote.lot_id).first()
    return CreneauVoteOut(
        id=vote.id, lot_id=vote.lot_id,
        lot_numero=lot_row.numero if lot_row else "",
        dispo=vote.dispo,
    )


@router.post("/ag/{ag_id}/choisir-creneau/{creneau_id}", response_model=AGOut)
def choisir_creneau(ag_id: int, creneau_id: int, db: Session = Depends(get_db), user: User = Depends(require_syndic)):
    """Fixe la date/heure de l'AG sur le créneau retenu et passe l'AG en 'convoquée'."""
    ag = db.query(AG).filter(AG.id == ag_id).first()
    if not ag:
        raise HTTPException(404, "AG introuvable")
    c = db.query(AgCreneau).filter(AgCreneau.id == creneau_id, AgCreneau.ag_id == ag.id).first()
    if not c:
        raise HTTPException(404, "Créneau introuvable pour cette AG")
    ag.date = c.debut.date()
    ag.heure = c.debut.strftime("%H:%M")
    ag.statut = "convoquee"
    db.commit()
    db.refresh(ag)
    return _ag_out(db, ag)


# ---------- Invitations (convocations par email) ----------
@router.get("/ag/{ag_id}/invitations", response_model=list[InvitationOut])
def list_invitations(ag_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ag = db.query(AG).filter(AG.id == ag_id).first()
    if not ag:
        raise HTTPException(404, "AG introuvable")
    invs = db.query(Invitation).filter(Invitation.ag_id == ag.id).order_by(Invitation.date_envoi.desc()).all()
    out = []
    for i in invs:
        personne = db.query(Personne).filter(Personne.id == i.personne_id).first()
        out.append(InvitationOut(
            id=i.id,
            personne_nom=f"{personne.prenom} {personne.nom}".strip() if personne else "?",
            personne_email=personne.email if personne else "",
            date_envoi=i.date_envoi,
            statut=i.statut,
            message=i.message,
        ))
    return out


@router.post("/ag/{ag_id}/invitations", response_model=InvitationsResult)
def envoyer_invitations(ag_id: int, db: Session = Depends(get_db), user: User = Depends(require_syndic)):
    """Envoie la convocation par email à tous les propriétaires ayant une adresse."""
    ag = db.query(AG).filter(AG.id == ag_id).first()
    if not ag:
        raise HTTPException(404, "AG introuvable")
    copro = db.query(Copropriete).filter(Copropriete.id == ag.copropriete_id).first()
    if not copro:
        raise HTTPException(404, "Copropriété introuvable")

    lots = db.query(Lot).filter(Lot.copropriete_id == copro.id).all()
    proprietaires = {}
    for lot in lots:
        if lot.proprietaire_id:
            proprietaires[lot.proprietaire_id] = True
    personnes = db.query(Personne).filter(Personne.id.in_(list(proprietaires.keys()))).all() if proprietaires else []

    corps = convocation_texte(copro, ag, ag.resolutions, user.nom)
    sujet = f"Convocation {ag.type_ag.replace('_', ' ')} — {copro.nom} ({ag.date.strftime('%d/%m/%Y')})"

    envoyes = 0
    sans_email = 0
    erreurs = []
    for p in personnes:
        if not p.email:
            sans_email += 1
            continue
        try:
            envoyer_email(copro, p.email, sujet, corps)
            statut = "envoye"
            message = ""
        except EmailError as e:
            statut = "erreur"
            message = str(e)
            erreurs.append(f"{p.nom}: {e}")
        inv = Invitation(
            ag_id=ag.id, personne_id=p.id,
            date_envoi=datetime.now(), statut=statut, message=message,
        )
        db.add(inv)
        if statut == "envoye":
            envoyes += 1
    db.commit()
    return InvitationsResult(envoyes=envoyes, sans_email=sans_email, erreurs=erreurs)
