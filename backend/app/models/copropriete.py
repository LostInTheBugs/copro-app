from sqlalchemy import Column, Integer, String, Boolean, Float
from sqlalchemy.orm import relationship
from app.core.database import Base


class Copropriete(Base):
    __tablename__ = "coproprietes"
    id = Column(Integer, primary_key=True)
    nom = Column(String, nullable=False)
    adresse = Column(String, default="")
    ville = Column(String, default="")
    code_postal = Column(String, default="")
    annee_construction = Column(Integer, nullable=True)
    regles_pays = Column(String, default="FR")
    devise = Column(String, default="EUR")
    # Fonds de travaux (obligatoire en France depuis la loi ALUR,
    # plus d'exemption < 10 lots : taux minimum 5 % du budget prévisionnel)
    fonds_travaux_actif = Column(Boolean, default=True)
    fonds_travaux_taux_pct = Column(Float, default=5.0)
    fonds_travaux_compte = Column(String, default="")
    compte_bancaire_separe = Column(String, default="")
    notes = Column(String, default="")

    users = relationship("User", back_populates="copropriete")
    lots = relationship("Lot", back_populates="copropriete", cascade="all, delete-orphan")
    personnes = relationship("Personne", back_populates="copropriete", cascade="all, delete-orphan")
    exercices = relationship("Exercice", back_populates="copropriete", cascade="all, delete-orphan")
    ags = relationship("AG", back_populates="copropriete", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="copropriete", cascade="all, delete-orphan")
    entreteins = relationship("Entretien", back_populates="copropriete", cascade="all, delete-orphan")
