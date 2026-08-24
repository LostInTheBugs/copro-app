"""Isolation multi-copropriétés : accès aux objets par identifiant.

Tout accès à un objet par son id doit vérifier que l'objet appartient à la
copropriété active, sinon renvoyer **404** (on ne divulgue pas l'existence
d'objets d'une autre copropriété — jamais de 403 ici).
"""
from fastapi import HTTPException
from sqlalchemy.orm import Session


def get_owned(db: Session, model, obj_id: int, copro, label: str = "Élément",
              message: str | None = None):
    """Récupère un objet en garantissant qu'il appartient à la copropriété active.

    - `label` : utilisé pour le message par défaut « {label} introuvable ».
    - `message` : message d'erreur exact à conserver (prioritaire sur `label`).
    """
    obj = (db.query(model)
           .filter(model.id == obj_id, model.copropriete_id == copro.id)
           .first())
    if not obj:
        raise HTTPException(404, message or f"{label} introuvable")
    return obj


def get_owned_via(db: Session, model, parent_model, obj_id: int, copro,
                  parent_fk: str, label: str = "Élément",
                  message: str | None = None):
    """Récupère un objet enfant (sans colonne `copropriete_id`) en garantissant
    que son parent appartient à la copropriété active.

    - `parent_fk` : colonne du modèle enfant qui référence le parent
      (ex. "ag_id", "exercice_id").
    """
    fk_col = getattr(model, parent_fk)
    obj = (db.query(model)
           .join(parent_model, fk_col == parent_model.id)
           .filter(model.id == obj_id, parent_model.copropriete_id == copro.id)
           .first())
    if not obj:
        raise HTTPException(404, message or f"{label} introuvable")
    return obj
