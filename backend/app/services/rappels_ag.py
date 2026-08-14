"""Rappel automatique des convocations d'AG (cron).

Le scheduler appelle run_rappels_ag() avec les relances automatiques : pour
chaque AG à venir avec un rappel configuré (rappel_jours > 0) et pas encore
convoquée, la convocation est envoyée à partir du jour J = date_ag − rappel_jours
(une seule fois ; anti-doublon via ag.convocation_envoyee).
"""
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.ag import AG
from app.models.copropriete import Copropriete
from app.models.user import User
from app.routes.ag import envoyer_convocations


def run_rappels_ag(db: Session, maintenant: datetime | None = None) -> dict:
    """Envoie les convocations automatiques des AG à venir.

    Retour : {"ag_rappel": n, "convocations": n, "sans_email": n, "erreurs": [...]}
    """
    maintenant = maintenant or datetime.now()
    stats = {"ag_rappel": 0, "convocations": 0, "sans_email": 0, "erreurs": []}
    ags = (db.query(AG)
           .filter(AG.date >= maintenant.date(), AG.rappel_jours > 0,
                   AG.convocation_envoyee == False)  # noqa: E712
           .all())
    for ag in ags:
        date_rappel = ag.date - timedelta(days=ag.rappel_jours)
        if maintenant.date() < date_rappel:
            continue  # pas encore le moment
        copro = db.query(Copropriete).filter(Copropriete.id == ag.copropriete_id).first()
        if not copro:
            continue
        syndic_nom = "Le syndic"
        syndic = (db.query(User).filter(User.copropriete_id == copro.id, User.role == "syndic").first())
        if syndic and syndic.nom:
            syndic_nom = syndic.nom
        res = envoyer_convocations(db, ag, copro, syndic_nom, marquer_envoyee=True)
        stats["ag_rappel"] += 1
        stats["convocations"] += res.envoyes
        stats["sans_email"] += res.sans_email
        stats["erreurs"].extend(res.erreurs)
    return stats
