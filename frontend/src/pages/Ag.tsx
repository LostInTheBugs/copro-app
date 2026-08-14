import { useEffect, useState } from "react";
import { api } from "../api";
import { useUser } from "../auth";
import type { AG, Lot, Resolution, Majorite } from "../types";
import { fmtDate } from "../types";
import { Button, Card, Input, Modal, Select, Badge, Empty } from "../components/ui";

export default function Ag() {
  const { user } = useUser();
  const isSyndic = user?.role === "syndic";
  const [ags, setAgs] = useState<AG[]>([]);
  const [lots, setLots] = useState<Lot[]>([]);
  const [majorites, setMajorites] = useState<Record<string, Majorite>>({});
  const [modal, setModal] = useState<null | { type: "ag" } | { type: "resolution"; agId: number }>(null);
  const [error, setError] = useState("");

  async function load() {
    const [a, l, m] = await Promise.all([
      api.get<AG[]>("/ag"),
      api.get<Lot[]>("/lots"),
      api.get<Record<string, Majorite>>("/majorites"),
    ]);
    setAgs(a);
    setLots(l);
    setMajorites(m);
  }
  useEffect(() => { load(); }, []);

  const total = lots.reduce((s, l) => s + l.tantiemes, 0);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-800">Assemblées générales</h1>
          <p className="text-sm text-slate-500">
            Résolutions, votes par lots et calcul automatique des majorités légales
          </p>
        </div>
        {isSyndic && <Button onClick={() => setModal({ type: "ag" })}>+ Nouvelle AG</Button>}
      </div>

      {error && <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}

      {ags.length === 0 ? (
        <Empty text="Aucune assemblée. Créez la prochaine AG annuelle : convocation, ordre du jour, votes et PV." />
      ) : (
        ags.map((ag) => (
          <Card
            key={ag.id}
            title={
              <span className="flex items-center gap-2">
                {ag.type_ag === "consultation_ecrite" ? "Consultation écrite" : ag.type_ag === "extraordinaire" ? "AG extraordinaire" : "AG annuelle"}
                <span className="text-slate-500">·</span>
                {fmtDate(ag.date)}
                {ag.lieu && <span className="font-normal text-slate-500">· {ag.lieu}</span>}
              </span>
            }
            action={
              <div className="flex items-center gap-2">
                <Badge color={ag.statut === "terminee" ? "green" : ag.statut === "convoquee" ? "indigo" : "amber"}>
                  {ag.statut === "terminee" ? "Terminée" : ag.statut === "convoquee" ? "Convoquée" : "Projet"}
                </Badge>
                {isSyndic && (
                  <Button variant="ghost" className="px-2 py-1 text-xs" onClick={() => setModal({ type: "resolution", agId: ag.id })}>
                    + Résolution
                  </Button>
                )}
              </div>
            }
          >
            {ag.resolutions.length === 0 ? (
              <Empty text="Aucune résolution à l'ordre du jour." />
            ) : (
              <div className="space-y-4">
                {ag.resolutions.map((r) => (
                  <ResolutionCard key={r.id} r={r} lots={lots} total={total} majorites={majorites} isSyndic={isSyndic} onChanged={load} onError={setError} />
                ))}
              </div>
            )}
          </Card>
        ))
      )}

      {modal?.type === "ag" && <AgModal onClose={() => setModal(null)} onSaved={() => { setModal(null); load(); }} onError={setError} />}
      {modal?.type === "resolution" && (
        <ResolutionModal agId={modal.agId} majorites={majorites} onClose={() => setModal(null)} onSaved={() => { setModal(null); load(); }} onError={setError} />
      )}
    </div>
  );
}

function ResolutionCard({ r, lots, total, majorites, isSyndic, onChanged, onError }: {
  r: Resolution; lots: Lot[]; total: number; majorites: Record<string, Majorite>;
  isSyndic: boolean; onChanged: () => void; onError: (e: string) => void;
}) {
  const res = r.resultat;
  const pct = total > 0 ? (res ? (res.pour / total) * 100 : 0) : 0;
  const majorite = majorites[r.majorite];

  async function vote(lotId: number, voix: string) {
    try {
      await api.post(`/resolutions/${r.id}/votes`, { lot_id: lotId, voix });
      await api.post(`/resolutions/${r.id}/calculer`);
      onChanged();
    } catch (e) { onError(e instanceof Error ? e.message : "Erreur"); }
  }

  return (
    <div className="rounded-lg border border-slate-200 p-4">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="font-medium text-slate-800">
            <span className="mr-2 rounded bg-slate-100 px-1.5 py-0.5 text-xs font-bold text-slate-500">Résolution {r.numero}</span>
            {r.libelle}
          </p>
          <p className="mt-0.5 text-xs text-slate-500">{majorite?.label ?? r.majorite} · {majorite?.description ?? ""}</p>
          {r.texte && <p className="mt-1 text-xs text-slate-500">{r.texte}</p>}
        </div>
        <div className="flex items-center gap-2">
          {r.statut === "a_voter" && <Badge color="amber">À voter</Badge>}
          {r.statut === "adoptee" && <Badge color="green">Adoptée</Badge>}
          {r.statut === "rejetee" && <Badge color="red">Rejetée</Badge>}
        </div>
      </div>

      {res && (
        <div className="mt-3">
          <div className="flex items-center gap-3 text-xs text-slate-500">
            <span>
              Pour : <b className="text-emerald-600 tabular-nums">{res.pour}‰</b>
            </span>
            <span>
              Contre : <b className="text-red-600 tabular-nums">{res.contre}‰</b>
            </span>
            <span>
              Abstention : <b className="tabular-nums">{res.abstention}‰</b>
            </span>
            <span className="ml-auto font-medium">{pct.toFixed(0)} % des millièmes pour</span>
          </div>
          <div className="mt-1.5 flex h-2 overflow-hidden rounded-full bg-slate-100">
            <div className="bg-emerald-500" style={{ width: `${(res.pour / total) * 100}%` }} />
            <div className="bg-red-400" style={{ width: `${(res.contre / total) * 100}%` }} />
            <div className="bg-slate-300" style={{ width: `${(res.abstention / total) * 100}%` }} />
          </div>
          {res.regime_deux && (
            <p className="mt-1.5 text-xs font-medium text-indigo-600">ℹ {res.detail}</p>
          )}
        </div>
      )}

      {isSyndic && (
        <div className="mt-3 grid grid-cols-2 gap-1.5 sm:grid-cols-4 lg:grid-cols-6">
          {lots.map((lot) => {
            const v = r.votes.find((x) => x.lot_id === lot.id);
            const current = v?.voix ?? "null";
            return (
              <div key={lot.id} className="rounded border border-slate-200 p-1.5">
                <p className="mb-1 text-center text-xs font-semibold text-slate-600">
                  Lot {lot.numero} <span className="font-normal text-slate-500">({lot.tantiemes}‰)</span>
                </p>
                <div className="grid grid-cols-3 gap-0.5 text-center">
                  {(["pour", "contre", "abstention"] as const).map((voix) => (
                    <button
                      key={voix}
                      onClick={() => vote(lot.id, voix)}
                      className={`rounded py-1 text-[11px] font-medium transition-colors ${
                        current === voix
                          ? voix === "pour"
                            ? "bg-emerald-500 text-white"
                            : voix === "contre"
                              ? "bg-red-500 text-white"
                              : "bg-slate-400 text-white"
                          : "bg-slate-50 text-slate-500 hover:bg-slate-100"
                      }`}
                    >
                      {voix === "pour" ? "Pour" : voix === "contre" ? "Contre" : "Abst."}
                    </button>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function AgModal({ onClose, onSaved, onError }: { onClose: () => void; onSaved: () => void; onError: (e: string) => void }) {
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10));
  const [typeAg, setTypeAg] = useState("annuelle");
  const [statut, setStatut] = useState("projet");
  const [lieu, setLieu] = useState("");
  async function save() {
    try {
      await api.post("/ag", { date, type_ag: typeAg, statut, lieu, notes: "" });
      onSaved();
    } catch (e) { onError(e instanceof Error ? e.message : "Erreur"); }
  }
  return (
    <Modal open title="Nouvelle assemblée" onClose={onClose}>
      <div className="space-y-3">
        <Input label="Date" type="date" value={date} onChange={(e) => setDate(e.target.value)} />
        <Select label="Type" value={typeAg} onChange={(e) => setTypeAg(e.target.value)}>
          <option value="annuelle">AG annuelle</option>
          <option value="extraordinaire">AG extraordinaire</option>
          <option value="consultation_ecrite">Consultation écrite (unanimité)</option>
        </Select>
        <Select label="Statut" value={statut} onChange={(e) => setStatut(e.target.value)}>
          <option value="projet">Projet</option>
          <option value="convoquee">Convoquée</option>
          <option value="terminee">Terminée</option>
        </Select>
        <Input label="Lieu" value={lieu} onChange={(e) => setLieu(e.target.value)} placeholder="Chez M. Durand" />
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={onClose}>Annuler</Button>
          <Button onClick={save}>Créer</Button>
        </div>
      </div>
    </Modal>
  );
}

function ResolutionModal({ agId, majorites, onClose, onSaved, onError }: {
  agId: number; majorites: Record<string, Majorite>; onClose: () => void; onSaved: () => void; onError: (e: string) => void;
}) {
  const [numero, setNumero] = useState("1");
  const [libelle, setLibelle] = useState("");
  const [texte, setTexte] = useState("");
  const [majorite, setMajorite] = useState("art24");
  async function save() {
    try {
      await api.post(`/ag/${agId}/resolutions`, { numero: Number(numero), libelle, texte, majorite });
      onSaved();
    } catch (e) { onError(e instanceof Error ? e.message : "Erreur"); }
  }
  return (
    <Modal open title="Nouvelle résolution" onClose={onClose}>
      <div className="space-y-3">
        <div className="grid grid-cols-3 gap-3">
          <Input label="N°" type="number" value={numero} onChange={(e) => setNumero(e.target.value)} />
          <Select label="Majorité requise" value={majorite} onChange={(e) => setMajorite(e.target.value)} className="col-span-2">
            {Object.entries(majorites).map(([k, m]) => (
              <option key={k} value={k}>{m.label}</option>
            ))}
          </Select>
        </div>
        <Input label="Libellé" value={libelle} onChange={(e) => setLibelle(e.target.value)} placeholder="Approbation des comptes de l'exercice précédent" />
        <label className="block text-sm">
          <span className="mb-1 block font-medium text-slate-600">Texte détaillé (optionnel)</span>
          <textarea
            value={texte}
            onChange={(e) => setTexte(e.target.value)}
            rows={3}
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          />
        </label>
        {majorite && majorites[majorite] && (
          <p className="text-xs text-slate-500">{majorites[majorite].description}</p>
        )}
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={onClose}>Annuler</Button>
          <Button onClick={save}>Ajouter</Button>
        </div>
      </div>
    </Modal>
  );
}
