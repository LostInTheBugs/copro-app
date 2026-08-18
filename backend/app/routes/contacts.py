from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user, require_syndic
from app.models.user import User
from app.models.contact import Contact
from app.routes.copro import get_or_create_copro
from app.schemas import ContactIn, ContactOut

router = APIRouter(prefix="/api/contacts", tags=["contacts"])

_TYPES = {
    "entreprise": "Entreprise",
    "artisan": "Artisan",
    "fournisseur": "Fournisseur",
    "institution": "Institution / organisme",
    "autre": "Autre",
}

_CATEGORIES = {
    "plomberie": "Plomberie / sanitaire",
    "electricite": "Électricité",
    "chauffage": "Chauffage / climatisation",
    "toiture": "Toiture / couverture",
    "nettoyage": "Nettoyage / ménage",
    "espace_vert": "Espaces verts",
    "securite": "Sécurité / incendie",
    "assurance": "Assurance",
    "energie": "Énergie",
    "telecom": "Télécom / internet",
    "autres": "Autres",
}


@router.get("", response_model=list[ContactOut])
def liste(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    copro = get_or_create_copro(db, user)
    return db.query(Contact).filter(Contact.copropriete_id == copro.id).order_by(Contact.nom).all()


@router.post("", response_model=ContactOut)
def creer(data: ContactIn, db: Session = Depends(get_db), user: User = Depends(require_syndic)):
    copro = get_or_create_copro(db, user)
    c = Contact(copropriete_id=copro.id, **data.model_dump())
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


@router.put("/{contact_id}", response_model=ContactOut)
def modifier(contact_id: int, data: ContactIn, db: Session = Depends(get_db), user: User = Depends(require_syndic)):
    c = db.query(Contact).filter(Contact.id == contact_id).first()
    if not c:
        raise HTTPException(404, "Contact introuvable")
    for k, v in data.model_dump().items():
        setattr(c, k, v)
    db.commit()
    db.refresh(c)
    return c


@router.delete("/{contact_id}")
def supprimer(contact_id: int, db: Session = Depends(get_db), user: User = Depends(require_syndic)):
    c = db.query(Contact).filter(Contact.id == contact_id).first()
    if not c:
        raise HTTPException(404, "Contact introuvable")
    db.delete(c)
    db.commit()
    return {"ok": True}


@router.get("/types")
def types():
    return _TYPES


@router.get("/categories")
def categories():
    return _CATEGORIES
