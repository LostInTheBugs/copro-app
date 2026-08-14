import { useEffect, useState } from "react";
import { api } from "../api";
import { useUser } from "../auth";
import type { Copro, User } from "../types";
import { Button, Card, Input, Modal, Select, Badge } from "../components/ui";

export default function Settings() {
  const { user: me } = useUser();
  const isSyndic = me?.role === "syndic";
  const [copro, setCopro] = useState<Copro | null>(null);
  const [users, setUsers] = useState<User[]>([]);
  const [modal, setModal] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get<Copro>("/copro").then(setCopro).catch(() => {});
    api.get<User[]>("/auth/users").then(setUsers).catch(() => {});
  }, []);

  async function saveCopro() {
    if (!copro) return;
    setSaved(false);
    setError("");
    try {
      const updated = await api.put<Copro>("/copro", {
        nom: copro.nom, adresse: copro.adresse, ville: copro.ville,
        code_postal: copro.code_postal, annee_construction: copro.annee_construction,
        fonds_travaux_actif: copro.fonds_travaux_actif,
        fonds_travaux_taux_pct: copro.fonds_travaux_taux_pct,
        fonds_travaux_compte: copro.fonds_travaux_compte,
        compte_bancaire_separe: copro.compte_bancaire_separe,
        notes: copro.notes,
      });
      setCopro(updated);
      setSaved(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erreur");
    }
  }

  if (!copro) return null;

  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <h1 className="text-xl font-bold text-slate-800">Réglages</h1>
        <p className="text-sm text-slate-500">Copropriété, fonds de travaux et comptes utilisateurs</p>
      </div>

      {error && <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}
      {saved && <p className="rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-700">Modifications enregistrées ✓</p>}

      <Card title="Copropriété">
        <div className="space-y-3">
          <Input label="Nom" value={copro.nom} onChange={(e) => setCopro({ ...copro, nom: e.target.value })} />
          <Input label="Adresse" value={copro.adresse} onChange={(e) => setCopro({ ...copro, adresse: e.target.value })} />
          <div className="grid grid-cols-3 gap-3">
            <Input label="Code postal" value={copro.code_postal} onChange={(e) => setCopro({ ...copro, code_postal: e.target.value })} />
            <Input label="Ville" className="col-span-2" value={copro.ville} onChange={(e) => setCopro({ ...copro, ville: e.target.value })} />
          </div>
          <Input
            label="Année de construction"
            type="number"
            value={copro.annee_construction ?? ""}
            onChange={(e) => setCopro({ ...copro, annee_construction: e.target.value ? Number(e.target.value) : null })}
          />
          <Input label="Compte bancaire séparé (syndicat)" value={copro.compte_bancaire_separe} onChange={(e) => setCopro({ ...copro, compte_bancaire_separe: e.target.value })} placeholder="IBAN / référence" />
          {isSyndic && <Button onClick={saveCopro}>Enregistrer</Button>}
        </div>
      </Card>

      <Card title="Fonds de travaux">
        <div className="space-y-3">
          <p className="rounded-lg bg-indigo-50 px-3 py-2 text-xs leading-relaxed text-indigo-800">
            <b>Obligation légale (France)</b> : fonds de travaux obligatoire dès 10 ans après réception des travaux,
            quel que soit le nombre de lots. Cotisation annuelle minimale : 5 % du budget prévisionnel
            (ou 2,5 % du plan pluriannuel de travaux + 5 % du budget si PPT voté). Versement sur compte séparé,
            montant voté chaque année en AG.
          </p>
          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={copro.fonds_travaux_actif}
              onChange={(e) => setCopro({ ...copro, fonds_travaux_actif: e.target.checked })}
            />
            Fonds de travaux actif (inclus dans les appels de fonds)
          </label>
          <div className="grid grid-cols-2 gap-3">
            <Input
              label="Taux (%)"
              type="number"
              step="0.5"
              value={copro.fonds_travaux_taux_pct}
              onChange={(e) => setCopro({ ...copro, fonds_travaux_taux_pct: Number(e.target.value) })}
            />
            <Input label="Compte dédié" value={copro.fonds_travaux_compte} onChange={(e) => setCopro({ ...copro, fonds_travaux_compte: e.target.value })} placeholder="IBAN / référence" />
          </div>
          {isSyndic && <Button onClick={saveCopro}>Enregistrer</Button>}
        </div>
      </Card>

      {me?.role === "syndic" && (
        <Card
          title="Comptes utilisateurs"
          action={<Button onClick={() => setModal(true)}>+ Ajouter</Button>}
        >
          <div className="space-y-2">
            {users.map((u) => (
              <div key={u.id} className="flex items-center justify-between rounded-lg border border-slate-100 px-3 py-2">
                <div>
                  <p className="text-sm font-medium text-slate-800">{u.nom}</p>
                  <p className="text-xs text-slate-500">{u.email}</p>
                </div>
                <div className="flex items-center gap-2">
                  <Badge color={u.role === "syndic" ? "indigo" : "slate"}>
                    {u.role === "syndic" ? "Syndic" : "Copropriétaire"}
                  </Badge>
                  {u.id !== me.id && (
                    <button
                      onClick={async () => { await api.del(`/auth/users/${u.id}`); setUsers(await api.get("/auth/users")); }}
                      className="rounded px-2 py-1 text-xs font-medium text-red-600 hover:bg-red-50"
                    >
                      ✕
                    </button>
                  )}
                </div>
              </div>
            ))}
            <p className="pt-1 text-xs text-slate-500">
              Les copropriétaires peuvent consulter la situation de la copropriété. Seul le syndic peut modifier.
            </p>
          </div>
        </Card>
      )}

      {modal && <UserModal onClose={() => setModal(false)} onSaved={async () => { setModal(false); setUsers(await api.get("/auth/users")); }} onError={setError} />}
    </div>
  );
}

function UserModal({ onClose, onSaved, onError }: { onClose: () => void; onSaved: () => void; onError: (e: string) => void }) {
  const [nom, setNom] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("membre");
  async function save() {
    try {
      await api.post("/auth/users", { nom, email, password, role });
      onSaved();
    } catch (e) { onError(e instanceof Error ? e.message : "Erreur"); }
  }
  return (
    <Modal open title="Nouvel utilisateur" onClose={onClose}>
      <div className="space-y-3">
        <Input label="Nom" value={nom} onChange={(e) => setNom(e.target.value)} placeholder="Jean Dupont" />
        <Input label="Email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
        <Input label="Mot de passe initial" value={password} onChange={(e) => setPassword(e.target.value)} minLength={6} />
        <Select label="Rôle" value={role} onChange={(e) => setRole(e.target.value)}>
          <option value="membre">Copropriétaire (consultation)</option>
          <option value="syndic">Syndic</option>
        </Select>
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={onClose}>Annuler</Button>
          <Button onClick={save}>Créer</Button>
        </div>
      </div>
    </Modal>
  );
}
