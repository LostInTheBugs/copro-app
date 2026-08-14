from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


# ---------- Auth / Users ----------
class RegisterRequest(BaseModel):
    email: str
    password: str
    nom: str


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    nom: str
    role: str


class UserCreate(BaseModel):
    email: str
    password: str
    nom: str
    role: str = "membre"


# ---------- Copropriete ----------
class CoproOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nom: str
    adresse: str = ""
    ville: str = ""
    code_postal: str = ""
    annee_construction: Optional[int] = None
    regles_pays: str = "FR"
    devise: str = "EUR"
    fonds_travaux_actif: bool = True
    fonds_travaux_taux_pct: float = 5.0
    fonds_travaux_compte: str = ""
    compte_bancaire_separe: str = ""
    notes: str = ""


class CoproUpdate(BaseModel):
    nom: Optional[str] = None
    adresse: Optional[str] = None
    ville: Optional[str] = None
    code_postal: Optional[str] = None
    annee_construction: Optional[int] = None
    fonds_travaux_actif: Optional[bool] = None
    fonds_travaux_taux_pct: Optional[float] = None
    fonds_travaux_compte: Optional[str] = None
    compte_bancaire_separe: Optional[str] = None
    notes: Optional[str] = None


# ---------- Personnes ----------
class PersonneIn(BaseModel):
    nom: str
    prenom: str = ""
    email: str = ""
    telephone: str = ""
    est_proprietaire: bool = True
    est_occupant: bool = True
    notes: str = ""


class PersonneOut(PersonneIn):
    model_config = ConfigDict(from_attributes=True)
    id: int


# ---------- Lots ----------
class LotIn(BaseModel):
    numero: str
    designation: str = ""
    type: str = "appartement"
    tantiemes: int = 0
    surface_m2: Optional[float] = None
    proprietaire_id: Optional[int] = None
    occupant_id: Optional[int] = None
    notes: str = ""


class LotOut(LotIn):
    model_config = ConfigDict(from_attributes=True)
    id: int


class LotSolde(BaseModel):
    lot: LotOut
    proprietaire: Optional[PersonneOut] = None
    occupant: Optional[PersonneOut] = None
    total_appels: float = 0.0
    total_appels_fonds: float = 0.0
    total_encaisse: float = 0.0
    solde: float = 0.0


# ---------- Exercices / budget ----------
class ExerciceIn(BaseModel):
    annee: int
    cloture: bool = False


class BudgetLineIn(BaseModel):
    libelle: str
    montant: float = 0.0
    type_repartition: str = "generale"


class BudgetLineOut(BudgetLineIn):
    model_config = ConfigDict(from_attributes=True)
    id: int


class ExerciceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    annee: int
    cloture: bool = False
    budget_total: float = 0.0


# ---------- Appels de fonds ----------
class AppelIn(BaseModel):
    libelle: str
    date_emission: date
    date_echeance: Optional[date] = None
    montant_total: float = 0.0
    inclut_fonds_travaux: bool = False


class AppelLotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    lot_id: int
    lot_numero: str = ""
    montant_charges: float = 0.0
    montant_fonds_travaux: float = 0.0


class AppelOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    exercice_id: int
    libelle: str
    date_emission: date
    date_echeance: Optional[date] = None
    montant_total: float = 0.0
    inclut_fonds_travaux: bool = False
    fonds_travaux_montant: float = 0.0
    parts: List[AppelLotOut] = []


# ---------- Mouvements ----------
class MouvementIn(BaseModel):
    date: date
    libelle: str
    type: str  # encaissement | depense
    categorie: str = "autre"
    montant: float = 0.0
    lot_id: Optional[int] = None
    appel_id: Optional[int] = None


class MouvementOut(MouvementIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
    piece_path: str = ""


# ---------- Etat daté / récap ----------
class EtatDateLot(BaseModel):
    lot: LotOut
    appels_charges: float = 0.0
    appels_fonds: float = 0.0
    encaisse: float = 0.0
    solde: float = 0.0


class RecapOut(BaseModel):
    exercice_id: int
    annee: int
    budget_previsionnel: float = 0.0
    encaisse: float = 0.0
    depense: float = 0.0
    solde_caisse: float = 0.0
    fonds_travaux_encaisse: float = 0.0
    appels_en_cours: int = 0
    lots: List[EtatDateLot] = []


# ---------- AG / résolutions ----------
class AGIn(BaseModel):
    date: date
    type_ag: str = "annuelle"
    statut: str = "projet"
    lieu: str = ""
    notes: str = ""


class VoteIn(BaseModel):
    lot_id: int
    voix: str  # pour | contre | abstention | null


class ResolutionIn(BaseModel):
    numero: int = 1
    libelle: str
    texte: str = ""
    majorite: str = "art24"


class ResolutionResult(BaseModel):
    statut: str
    pour: float = 0.0
    contre: float = 0.0
    abstention: float = 0.0
    total: float = 0.0
    quorum: float = 0.0
    regime_deux: bool = False
    detail: str = ""


class VoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    lot_id: int
    voix: str


class ResolutionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    ag_id: int
    numero: int
    libelle: str
    texte: str = ""
    majorite: str = "art24"
    statut: str = "a_voter"
    votes: List[VoteOut] = []
    resultat: Optional[ResolutionResult] = None


class AGOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    date: date
    type_ag: str = "annuelle"
    statut: str = "projet"
    lieu: str = ""
    notes: str = ""
    resolutions: List[ResolutionOut] = []


# ---------- Documents ----------
class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    categorie: str = "autre"
    libelle: str
    fichier: str = ""
    date_ajout: date


# ---------- Carnet d'entretien ----------
class EntretienIn(BaseModel):
    date: date
    type_intervention: str = ""
    prestataire: str = ""
    cout: float = 0.0
    lot_id: Optional[int] = None
    description: str = ""


class EntretienOut(EntretienIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
