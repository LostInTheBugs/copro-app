from sqlalchemy import Column, Integer, String, ForeignKey, Date
from sqlalchemy.orm import relationship
from app.core.database import Base


class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True)
    copropriete_id = Column(Integer, ForeignKey("coproprietes.id"), nullable=False)
    categorie = Column(String, default="autre")
    # contrat | assurance | facture | devis | diagnostic | pv | convocation | autre
    libelle = Column(String, nullable=False)
    fichier = Column(String, default="")  # nom du fichier stocké
    date_ajout = Column(Date, nullable=False)

    copropriete = relationship("Copropriete", back_populates="documents")
