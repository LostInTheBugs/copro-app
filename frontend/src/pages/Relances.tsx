import { useCallback, useEffect, useState } from "react";
import { api } from "../api";
import { useUser } from "../auth";
import type { RelanceLot, Relance } from "../types";
import { fmtEUR, fmtDateTime } from "../types";
import { Button, Card, Badge, Empty } from "../components/ui";

export default function Relances() {
  const { user } = useUser();
  const isSyndic = user?.role === "syndic";
  const [etat, setEtat] = useState<RelanceLot[]>([]);
  const [historique, setHistorique] = useState<Relance[]>([]);
  const [selection, setSelection] = useState<Set<number>>(new Set());
  const [busy, setBusy] = useState(false);
  const [resultat, setResultat] = useState<{ envoyes: number; sans_email: number; erreurs: string[] } | null>(null);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    const [e, h] = await Promise.all([
      api.get<RelanceLot[]>("/relances"),
      api.get<Relance[]>("/relances/historique"),
    ]);
    setEtat(e);
    setHistorique(h);
    setSelection(new Set(e.filter((x) => x.solde > 0.005).map((x) => x.lot_id)));
  }, []);
  useEffect(() => { load().catch(() => {}); }, [load]);

  const enRetard = etat.filter((e) => e.solde > 0.005);
  const totalDu = enRetard.reduce((s, e) => s + e.solde, 0);

  function toggle(lotId: number) {
    setSelection((prev) => {
      const next = new Set(prev);
      if (next.has(lotId)) next.delete(lotId);
      else next.add(lotId);
      return next;
    });
  }

  async function envoyer() {
    setBusy(true);
    setResultat(null);
    setError("");
    try {
      const res = await api.post<{ envoyes: number; sans_email: number; erreurs: string[] }>("/relances/envoyer", {
        lot_ids: [...selection],
      });
      setResultat(res);
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erreur");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-slate-800">Relances d'impayés</h1>
        <p className="text-sm text-slate-500">
          {enRetard.length} lot(s) en retard · {fmtEUR(totalDu)} au total
        </p>
      </div>

      {error && <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}
      {resultat && (
        <p className="rounded-lg bg-indigo-50 px-3 py-2 text-sm text-indigo-800">
          {resultat.envoyes} relance(s) envoyée(s)
          {resultat.sans_email > 0 && ` · ${resultat.sans_email} propriétaire(s) sans adresse email`}
          {resultat.erreurs.length > 0 && <span className="block text-red-700">Échecs : {resultat.erreurs.join(" · ")}</span>}
        </p>
      )}

      <Card title="Situation par lot" action={
        isSyndic ? (
          <Button disabled={busy || selection.size === 0} onClick={envoyer}>
            {busy ? "Envoi…" : `Envoyer ${selection.size} relance(s)`}
          </Button>
        ) : undefined
      }>
        {etat.length === 0 ? (
          <Empty text="Aucun lot. Ajoutez d'abord les lots dans Lots & occupants." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100 text-left text-xs uppercase tracking-wide text-slate-500">
                  {isSyndic && <th className="py-2 pr-2" />}
                  <th className="px-3 py-2 font-medium">Lot</th>
                  <th className="px-3 py-2 font-medium">Propriétaire</th>
                  <th className="px-3 py-2 text-right font-medium">Charges appelées</th>
                  <th className="px-3 py-2 text-right font-medium">Fonds travaux</th>
                  <th className="px-3 py-2 text-right font-medium">Encaissé</th>
                  <th className="px-3 py-2 text-right font-medium">Solde</th>
                </tr>
              </thead>
              <tbody>
                {etat.map((e) => {
                  const enRetardLot = e.solde > 0.005;
                  return (
                    <tr key={e.lot_id} className="border-b border-slate-50 last:border-0">
                      {isSyndic && (
                        <td className="py-2 pr-2">
                          <input
                            type="checkbox"
                            checked={selection.has(e.lot_id)}
                            disabled={!enRetardLot}
                            onChange={() => toggle(e.lot_id)}
                            className="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                          />
                        </td>
                      )}
                      <td className="px-3 py-2 font-medium text-slate-700">Lot {e.lot_numero}</td>
                      <td className="px-3 py-2 text-slate-600">
                        {e.personne_nom}
                        {e.personne_email && <span className="block text-xs text-slate-400">{e.personne_email}</span>}
                      </td>
                      <td className="px-3 py-2 text-right tabular-nums text-slate-600">{fmtEUR(e.appels_charges)}</td>
                      <td className="px-3 py-2 text-right tabular-nums text-slate-600">{fmtEUR(e.appels_fonds)}</td>
                      <td className="px-3 py-2 text-right tabular-nums text-slate-600">{fmtEUR(e.encaisse)}</td>
                      <td className="px-3 py-2 text-right">
                        {enRetardLot ? (
                          <Badge color="red">{fmtEUR(e.solde)}</Badge>
                        ) : (
                          <Badge color="green">{fmtEUR(e.solde)}</Badge>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
        <p className="mt-2 text-xs text-slate-500">
          Les relances sont envoyées par email avec le détail : charges appelées, fonds de travaux, encaissements reçus
          et coordonnées de règlement. L'email utilise la configuration SMTP des Réglages.
        </p>
      </Card>

      <Card title="Historique des relances">
        {historique.length === 0 ? (
          <Empty text="Aucune relance envoyée pour le moment." />
        ) : (
          <ul className="space-y-1.5 text-sm">
            {historique.map((h) => (
              <li key={h.id} className="flex flex-wrap items-center gap-2">
                <span className="font-medium text-slate-700">Lot {h.lot_numero}</span>
                <span className="text-slate-500">{h.personne_nom}</span>
                <span className="ml-auto text-xs text-slate-400">{fmtDateTime(h.date_envoi)}</span>
                <span className="font-semibold tabular-nums text-red-600">{fmtEUR(h.montant_du)}</span>
                {h.statut === "envoye" ? <Badge color="green">envoyé</Badge> : <Badge color="red">erreur</Badge>}
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
