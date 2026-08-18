from sqlalchemy import Column, Integer, String, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.core.database import Base


class Contact(Base):
    """Contact externe de la copropriété (entreprise, fournisseur, artisan…)."""
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True)
    copropriete_id = Column(Integer, ForeignKey("coproprietes.id"), nullable=False)
    nom = Column(String, nullable=False)
    type = Column(String, default="entreprise")  # entreprise, artisan, fournisseur, institution, autre
    categorie = Column(String, default="autres")  # plomberie, electricite, chauffage, assurance, energie, telecom, nettoyage, securite, autres
    telephone = Column(String, default="")
    email = Column(String, default="")
    adresse = Column(String, default="")
    site_web = Column(String, default="")
    notes = Column(Text, default="")

    copropriete = relationship("Copropriete")
