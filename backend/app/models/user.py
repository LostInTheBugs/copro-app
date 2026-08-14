from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    nom = Column(String, nullable=False)
    role = Column(String, default="membre")  # syndic | membre
    copropriete_id = Column(Integer, ForeignKey("coproprietes.id"), nullable=True)
    copropriete = relationship("Copropriete", back_populates="users")
