import { useEffect, useState } from "react";
import { api } from "../api";
import { useUser } from "../auth";
import type { Entretien, Lot } from "../types";
import { fmtEUR, fmtDate } from "../types";
import { Button, Card, Input, Modal, Select, Empty } from "../components/ui";

export default function Carnet() {
  const { user } = useUser();
  const isSyndic = user?.role === "syndic";
  const [items, setItems] = useState<Entretien[]>([]);
  const [lots, setLots] = useState<Lot[]>([]);
  const [modal, setModal] = useState(false);
  const [error, setError] = useState("");

  async function load() {
    const [i, l] = await Promise.all([api.get<Entretien[]>("/carnet"), api.get<Lot[]>("/lots")]);
    setItems(i);
    setLots(l);
  }
  useEffect(() => { load().catch(() => {}); }, []);

  const total = items.reduce((s, i) => s + i.cout, 0);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-800">Carnet d'entretien</h1>
          <p className="text-sm text-slate-500">
            Historique des interventions sur l'immeuble (obligation légale du syndic)
          </p>
        </div>
        {isSyndic && <Button onClick={() => setModal(true)}>+ Intervention</Button>}
      </div>

      {error && <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}

      <div className="rounded-xl border border-slate-200 bg-white p-4 text-sm shadow-sm">
        <span className="font-medium text-slate-600">Coût total des interventions enregistrées : </span>
        <span className="font-bold text-slate-800">{fmtEUR(total)}</span>
      </div>

      {items.length === 0 ? (
        <Empty text="Aucune intervention enregistrée. Notez chaque visite du plombier, de l'électricien, l'entretien de la chaudière…" />
      ) : (
        <div className="space-y-3">
          {items.map((i) => {
            const lot = lots.find((l) => l.id === i.lot_id);
            return (
              <div key={i.id} className="flex items-start justify-between rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
                <div>
                  <p className="font-medium text-slate-800">
                    {i.type_intervention || "Intervention"}
                    {lot && <span className="ml-2 text-xs font-normal text-slate-500">Lot {lot.numero}</span>}
                  </p>
                  <p className="mt-0.5 text-xs text-slate-500">
                    {fmtDate(i.date)}
                    {i.prestataire && <> · {i.prestataire}</>}
                  </p>
                  {i.description && <p className="mt-1 text-sm text-slate-600">{i.description}</p>}
                </div>
                <div className="flex shrink-0 items-center gap-3">
                  <span className="font-bold tabular-nums text-slate-800">{fmtEUR(i.cout)}</span>
                  {isSyndic && (
                    <button
                      onClick={async () => { await api.del(`/carnet/${i.id}`); load(); }}
                      className="rounded-lg px-2 py-1 text-xs font-medium text-red-600 hover:bg-red-50"
                    >
                      ✕
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {modal && (
        <EntretienModal lots={lots} onClose={() => setModal(false)} onSaved={() => { setModal(false); load(); }} onError={setError} />
      )}
    </div>
  );
}

function EntretienModal({ lots, onClose, onSaved, onError }: {
  lots: Lot[]; onClose: () => void; onSaved: () => void; onError: (e: string) => void;
}) {
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10));
  const [type, setType] = useState("");
  const [prestataire, setPrestataire] = useState("");
  const [cout, setCout] = useState("");
  const [lotId, setLotId] = useState("");
  const [description, setDescription] = useState("");
  async function save() {
    try {
      await api.post("/carnet", {
        date, type_intervention: type, prestataire, cout: Number(cout) || 0,
        lot_id: lotId === "" ? null : Number(lotId), description,
      });
      onSaved();
    } catch (e) { onError(e instanceof Error ? e.message : "Erreur"); }
  }
  return (
    <Modal open title="Nouvelle intervention" onClose={onClose}>
      <div className="space-y-3">
        <Input label="Date" type="date" value={date} onChange={(e) => setDate(e.target.value)} />
        <Input label="Type d'intervention" value={type} onChange={(e) => setType(e.target.value)} placeholder="Entretien chaudière" />
        <Input label="Prestataire" value={prestataire} onChange={(e) => setPrestataire(e.target.value)} placeholder="Chauffagiste SARL" />
        <div className="grid grid-cols-2 gap-3">
          <Input label="Coût (€)" type="number" step="0.01" value={cout} onChange={(e) => setCout(e.target.value)} />
          <Select label="Lot concerné" value={lotId} onChange={(e) => setLotId(e.target.value)}>
            <option value="">Parties communes</option>
            {lots.map((l) => <option key={l.id} value={l.id}>Lot {l.numero}</option>)}
          </Select>
        </div>
        <label className="block text-sm">
          <span className="mb-1 block font-medium text-slate-600">Description</span>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={2}
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          />
        </label>
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={onClose}>Annuler</Button>
          <Button onClick={save}>Enregistrer</Button>
        </div>
      </div>
    </Modal>
  );
}
