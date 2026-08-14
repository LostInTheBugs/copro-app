import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import type { Recap } from "../types";
import { fmtEUR, fmtDate } from "../types";
import { Card, Stat, Badge, Empty } from "../components/ui";

export default function Dashboard() {
  const [recap, setRecap] = useState<Recap | null>(null);

  useEffect(() => {
    api.get<Recap>("/recap").then(setRecap).catch(() => {});
  }, []);

  if (!recap || recap.annee === 0) {
    return (
      <div className="space-y-6">
        <h1 className="text-xl font-bold text-slate-800">Tableau de bord</h1>
        <Empty text="Aucun exercice pour le moment. Créez l'exercice en cours dans l'onglet Comptes, puis ajoutez le budget prévisionnel et les appels de fonds." />
      </div>
    );
  }

  const tauxRecouvrement = recap.budget_previsionnel > 0 ? (recap.encaisse / recap.budget_previsionnel) * 100 : 0;
  const impayes = recap.lots.filter((l) => l.solde > 0.01);
  const totalImpayes = impayes.reduce((s, l) => s + l.solde, 0);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-800">Tableau de bord</h1>
          <p className="text-sm text-slate-500">Exercice {recap.annee}</p>
        </div>
        <Link
          to="/comptes"
          className="rounded-lg bg-indigo-600 px-3 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-700"
        >
          Gérer les comptes
        </Link>
      </div>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Stat label="Budget prévisionnel" value={fmtEUR(recap.budget_previsionnel)} />
        <Stat label="Encaissé" value={fmtEUR(recap.encaisse)} sub={`${tauxRecouvrement.toFixed(0)} % du budget`} accent />
        <Stat label="Dépensé" value={fmtEUR(recap.depense)} sub={`Solde en caisse : ${fmtEUR(recap.solde_caisse)}`} />
        <Stat label="Fonds de travaux" value={fmtEUR(recap.fonds_travaux_encaisse)} sub="Cotisations encaissées" />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card title="Situation par lot (état daté)">
          {recap.lots.length === 0 ? (
            <Empty text="Aucun lot — créez les lots dans l'onglet Lots & occupants." />
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100 text-left text-xs uppercase tracking-wide text-slate-500">
                  <th className="pb-2 font-medium">Lot</th>
                  <th className="pb-2 text-right font-medium">Appels</th>
                  <th className="pb-2 text-right font-medium">Payé</th>
                  <th className="pb-2 text-right font-medium">Solde</th>
                </tr>
              </thead>
              <tbody>
                {recap.lots.map((l) => (
                  <tr key={l.lot.id} className="border-b border-slate-50 last:border-0">
                    <td className="py-2.5">
                      <span className="font-medium text-slate-800">Lot {l.lot.numero}</span>
                      {l.lot.designation && <span className="ml-2 text-xs text-slate-500">{l.lot.designation}</span>}
                    </td>
                    <td className="py-2.5 text-right tabular-nums text-slate-600">
                      {fmtEUR(l.appels_charges + l.appels_fonds)}
                    </td>
                    <td className="py-2.5 text-right tabular-nums text-slate-600">{fmtEUR(l.encaisse)}</td>
                    <td className="py-2.5 text-right">
                      {Math.abs(l.solde) < 0.01 ? (
                        <span className="font-medium text-emerald-600">À jour</span>
                      ) : l.solde > 0 ? (
                        <span className="font-semibold text-red-600">{fmtEUR(l.solde)}</span>
                      ) : (
                        <span className="font-medium text-emerald-600">{fmtEUR(l.solde)}</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>

        <Card title="Impayés">
          {impayes.length === 0 ? (
            <div className="flex flex-col items-center gap-2 py-6 text-center">
              <span className="text-3xl">✅</span>
              <p className="text-sm text-slate-600">Tous les lots sont à jour.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {impayes.map((l) => (
                <div key={l.lot.id} className="flex items-center justify-between rounded-lg bg-red-50/60 px-3 py-2.5">
                  <div>
                    <p className="text-sm font-medium text-slate-800">Lot {l.lot.numero}</p>
                    <p className="text-xs text-slate-500">
                      {l.appels_charges + l.appels_fonds > 0
                        ? `${((l.encaisse / (l.appels_charges + l.appels_fonds)) * 100).toFixed(0)} % payé`
                        : "aucun appel"}
                    </p>
                  </div>
                  <span className="text-sm font-bold text-red-600">{fmtEUR(l.solde)}</span>
                </div>
              ))}
              <p className="pt-1 text-sm text-slate-600">
                Total des impayés : <span className="font-bold text-red-600">{fmtEUR(totalImpayes)}</span>
              </p>
            </div>
          )}
        </Card>
      </div>

      {recap.appels_en_cours > 0 && (
        <div className="flex items-center gap-2 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          <Badge color="amber">{recap.appels_en_cours}</Badge>
          <span>appel(s) de fonds émis avec une date d'échéance définie sur l'exercice {recap.annee}.</span>
        </div>
      )}
    </div>
  );
}
