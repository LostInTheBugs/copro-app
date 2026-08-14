from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import require_syndic
from app.models.user import User
from app.models.copropriete import Copropriete
from app.routes.copro import get_or_create_copro
from app.services.emailer import envoyer_email, EmailError
from app.schemas import SmtpConfigIn, SmtpTestResult

router = APIRouter(prefix="/api/smtp", tags=["smtp"])


@router.put("/config")
def update_smtp(
    data: SmtpConfigIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_syndic),
):
    """Met à jour la configuration SMTP (Réglages → Envoi des emails)."""
    copro = get_or_create_copro(db, user)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(copro, field, value)
    db.commit()
    return {"ok": True}


@router.post("/test", response_model=SmtpTestResult)
def test_smtp(
    data: SmtpConfigIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_syndic),
):
    """Envoie un email de test au syndic avec la configuration fournie."""
    copro = get_or_create_copro(db, user)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(copro, field, value)
    if not copro.email_expediteur:
        raise HTTPException(400, "Renseignez l'adresse expéditeur")
    try:
        envoyer_email(
            copro,
            copro.email_expediteur,
            "Test CoproApp",
            "Cet email confirme que la configuration SMTP de CoproApp fonctionne.",
        )
        db.commit()
        return SmtpTestResult(ok=True, detail="Email de test envoyé avec succès")
    except EmailError as e:
        return SmtpTestResult(ok=False, detail=str(e))
