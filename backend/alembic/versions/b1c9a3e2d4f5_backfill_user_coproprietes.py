"""backfill user_coproprietes (ancien backfill SQL du démarrage)

Historique : `migrate()` (app/core/database.py) insérait au démarrage une
liaison user→copro pour les comptes existants. Ce backfill devient une
migration à part entière, exécutée une seule fois par Alembic.

Sur une base existante stampée (production), la liaison a déjà été créée par
l'ancien code → cette migration ne fait rien (0 ligne dans user_coproprietes
n'est plus vrai). Sur une base neuve, les tables sont vides → no-op également.
Uniquement utile pour une base intermédiaire (schéma complet mais pas de
liaisons), d'où le INSERT … SELECT avec NOT EXISTS pour rester idempotent.

Revision ID: b1c9a3e2d4f5
Revises: ae4fc0457052
Create Date: 2026-08-24
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b1c9a3e2d4f5'
down_revision: Union[str, Sequence[str], None] = 'ae4fc0457052'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Crée la liaison user→copro principale pour les comptes sans liaison."""
    op.execute(
        """
        INSERT INTO user_coproprietes (user_id, copropriete_id, principale)
        SELECT u.id, u.copropriete_id, TRUE
        FROM users u
        WHERE u.copropriete_id IS NOT NULL
          AND NOT EXISTS (
              SELECT 1 FROM user_coproprietes uc
              WHERE uc.user_id = u.id AND uc.copropriete_id = u.copropriete_id
          )
        """
    )


def downgrade() -> None:
    """Supprime les liaisons créées par ce backfill (impossible de distinguer
    les liaisons préexistantes : on ne fait rien, la migration est un one-shot
    de données)."""
    pass
