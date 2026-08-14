from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class UserCopro(Base):
    """Liaison user ↔ copropriété (un user peut gérer plusieurs immeubles)."""
    __tablename__ = "user_coproprietes"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    copropriete_id = Column(Integer, ForeignKey("coproprietes.id"), nullable=False)
    principale = Column(Boolean, default=False)


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    nom = Column(String, nullable=False)
    role = Column(String, default="membre")  # syndic | membre
    copropriete_id = Column(Integer, ForeignKey("coproprietes.id"), nullable=True)
    copropriete = relationship("Copropriete", back_populates="users")
    coproprietes = relationship(
        "UserCopro", backref="user", cascade="all, delete-orphan",
        foreign_keys="UserCopro.user_id",
    )
