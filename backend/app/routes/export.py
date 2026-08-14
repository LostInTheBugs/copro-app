import csv
import io
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse, Response
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.lot import Lot
from app.models.personne import Personne
from app.models.exercice import Exercice
from app.models.appel import AppelFonds, AppelLot
from app.models.mouvement import Mouvement
from app.routes.copro import get_or_create_copro
from app.services.compte_gestion import generer_compte_gestion_pdf

router = APIRouter(prefix="/api/export", tags=["export"])


@router.get("/compte-gestion/{exercice_id}")
def compte_gestion(exercice_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Compte de gestion annuel en PDF (présenté en AG pour approbation)."""
    from app.models.copropriete import Copropriete
    copro = get_or_create_copro(db, user)
    ex = db.query(Exercice).filter(Exercice.id == exercice_id, Exercice.copropriete_id == copro.id).first()
    if not ex:
        raise HTTPException(404, "Exercice introuvable")
    pdf = generer_compte_gestion_pdf(copro, ex, db)
    nom = f"Compte_de_gestion_{ex.annee}_{copro.nom.replace(' ', '_')}.pdf"
    return Response(
        content=pdf.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{nom}"'},
    )


def _csv(data: list[list], headers: list[str]) -> StreamingResponse:
    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=";")
    writer.writerow(headers)
    writer.writerows(data)
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=export.csv"},
    )


@router.get("/registre")
def export_registre(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Données utiles pour la déclaration au registre des copropriétés
    (registre.coproprietes.gouv.fr)."""
    copro = get_or_create_copro(db, user)
    lots = db.query(Lot).filter(Lot.copropriete_id == copro.id).all()
    personnes = db.query(Personne).filter(Personne.copropriete_id == copro.id).all()
    rows = []
    for lot in lots:
        prop = lot.proprietaire
        rows.append([
            copro.nom, copro.adresse, copro.code_postal, copro.ville,
            lot.numero, lot.type, lot.tantiemes,
            prop.nom if prop else "", prop.prenom if prop else "",
            prop.email if prop else "",
        ])
    return _csv(rows, [
        "Copro", "Adresse", "Code postal", "Ville", "Lot", "Type",
        "Millièmes", "Propriétaire nom", "Propriétaire prénom", "Email",
    ])


@router.get("/compte-gestion")
def export_compte_gestion(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Compte de gestion annuel : appels, encaissements, dépenses par lot."""
    copro = get_or_create_copro(db, user)
    ex = db.query(Exercice).filter(Exercice.copropriete_id == copro.id).order_by(Exercice.annee.desc()).first()
    rows = []
    if ex:
        appels = db.query(AppelFonds).filter(AppelFonds.exercice_id == ex.id).all()
        for appel in appels:
            for part in appel.parts:
                lot = db.query(Lot).filter(Lot.id == part.lot_id).first()
                rows.append([
                    ex.annee, appel.libelle, "appel",
                    lot.numero if lot else "", part.montant_charges, part.montant_fonds_travaux,
                ])
        mouvements = db.query(Mouvement).filter(Mouvement.exercice_id == ex.id).all()
        for m in mouvements:
            lot = db.query(Lot).filter(Lot.id == m.lot_id).first() if m.lot_id else None
            rows.append([
                ex.annee, m.libelle, m.type, lot.numero if lot else "copro",
                m.montant if m.type == "depense" else 0, m.montant if m.type == "encaissement" else 0,
            ])
    return _csv(rows, ["Exercice", "Libellé", "Type", "Lot", "Dépense", "Encaissement"])
