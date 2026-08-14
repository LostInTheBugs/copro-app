from sqlalchemy import Column, Integer, String, ForeignKey, Date, Text
from sqlalchemy.orm import relationship
from app.core.database import Base


class AG(Base):
    __tablename__ = "ags"
    id = Column(Integer, primary_key=True)
    copropriete_id = Column(Integer, ForeignKey("coproprietes.id"), nullable=False)
    date = Column(Date, nullable=False)
    type_ag = Column(String, default="annuelle")  # annuelle | extraordinaire | consultation_ecrite
    statut = Column(String, default="projet")  # projet | convoquee | terminee
    lieu = Column(String, default="")
    notes = Column(Text, default="")

    copropriete = relationship("Copropriete", back_populates="ags")
    resolutions = relationship("Resolution", back_populates="ag", cascade="all, delete-orphan")


class Resolution(Base):
    __tablename__ = "resolutions"
    id = Column(Integer, primary_key=True)
    ag_id = Column(Integer, ForeignKey("ags.id"), nullable=False)
    numero = Column(Integer, default=1)
    libelle = Column(String, nullable=False)
    texte = Column(Text, default="")
    # art24 = majorité des voix exprimées (présents + représentés + correspondance)
    # art25 = majorité des voix de tous les copropriétaires
    # art26 = majorité des 2/3 des voix de tous les copropriétaires
    # unanimite = tous les copropriétaires
    majorite = Column(String, default="art24")
    statut = Column(String, default="a_voter")  # a_voter | adoptee | rejetee

    ag = relationship("AG", back_populates="resolutions")
    votes = relationship("Vote", back_populates="resolution", cascade="all, delete-orphan")


class Vote(Base):
    __tablename__ = "votes"
    id = Column(Integer, primary_key=True)
    resolution_id = Column(Integer, ForeignKey("resolutions.id"), nullable=False)
    lot_id = Column(Integer, ForeignKey("lots.id"), nullable=False)
    voix = Column(String, default="null")  # pour | contre | abstention | null

    resolution = relationship("Resolution", back_populates="votes")
    lot = relationship("Lot")
