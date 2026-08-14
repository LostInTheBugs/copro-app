from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class Lot(Base):
    __tablename__ = "lots"
    id = Column(Integer, primary_key=True)
    copropriete_id = Column(Integer, ForeignKey("coproprietes.id"), nullable=False)
    numero = Column(String, nullable=False)
    designation = Column(String, default="")  # ex: "Appartement T3"
    type = Column(String, default="appartement")  # appartement | cave | parking | commerce | autre
    tantiemes = Column(Integer, default=0)  # millièmes (total = 1000, stocké en millièmes)
    surface_m2 = Column(Float, nullable=True)
    proprietaire_id = Column(Integer, ForeignKey("personnes.id"), nullable=True)
    occupant_id = Column(Integer, ForeignKey("personnes.id"), nullable=True)
    notes = Column(String, default="")

    copropriete = relationship("Copropriete", back_populates="lots")
    proprietaire = relationship("Personne", foreign_keys=[proprietaire_id], back_populates="lots_proprietaire")
    occupant = relationship("Personne", foreign_keys=[occupant_id], back_populates="lots_occupant")
