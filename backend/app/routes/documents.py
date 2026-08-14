import os
import uuid
from datetime import date
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.core.database import get_db
from app.core.deps import get_current_user, require_syndic
from app.models.user import User
from app.models.document import Document
from app.routes.copro import get_or_create_copro
from app.schemas import DocumentOut

router = APIRouter(prefix="/api/documents", tags=["documents"])
settings = get_settings()

CATEGORIES = {"contrat", "assurance", "facture", "devis", "diagnostic", "pv", "convocation", "autre"}


@router.get("", response_model=list[DocumentOut])
def list_documents(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    copro = get_or_create_copro(db, user)
    return db.query(Document).filter(Document.copropriete_id == copro.id).order_by(Document.date_ajout.desc()).all()


@router.post("", response_model=DocumentOut)
async def upload_document(
    categorie: str = Form("autre"),
    libelle: str = Form(...),
    fichier: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_syndic),
):
    if categorie not in CATEGORIES:
        categorie = "autre"
    copro = get_or_create_copro(db, user)
    os.makedirs(settings.upload_dir, exist_ok=True)
    ext = os.path.splitext(fichier.filename or "")[1][:10]
    nom_stocke = f"{uuid.uuid4().hex}{ext}"
    path = os.path.join(settings.upload_dir, nom_stocke)
    content = await fichier.read()
    with open(path, "wb") as f:
        f.write(content)
    doc = Document(
        copropriete_id=copro.id,
        categorie=categorie,
        libelle=libelle,
        fichier=nom_stocke,
        date_ajout=date.today(),
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


@router.get("/{doc_id}/download")
def download_document(doc_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(404, "Document introuvable")
    path = os.path.join(settings.upload_dir, doc.fichier)
    if not os.path.exists(path):
        raise HTTPException(404, "Fichier manquant sur le serveur")
    return FileResponse(path, filename=doc.libelle)


@router.delete("/{doc_id}")
def delete_document(doc_id: int, db: Session = Depends(get_db), user: User = Depends(require_syndic)):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(404, "Document introuvable")
    path = os.path.join(settings.upload_dir, doc.fichier)
    if os.path.exists(path):
        os.remove(path)
    db.delete(doc)
    db.commit()
    return {"ok": True}
