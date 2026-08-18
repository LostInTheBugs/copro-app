import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import { useUser } from "../auth";
import type { Contact } from "../types";
import { Button, Card, Input, Modal, Select, Badge, Empty } from "../components/ui";

const TYPES: Record<string, string> = {
  entreprise: "Entreprise",
  artisan: "Artisan",
  fournisseur: "Fournisseur",
  institution: "Institution / organisme",
  autre: "Autre",
};

const CATEGORIES: Record<string, string> = {
  plomberie: "Plomberie / sanitaire",
  electricite: "Électricité",
  chauffage: "Chauffage / climatisation",
  toiture: "Toiture / couverture",
  nettoyage: "Nettoyage / ménage",
  espace_vert: "Espaces verts",
  securite: "Sécurité / incendie",
  assurance: "Assurance",
  energie: "Énergie",
  telecom: "Télécom / internet",
  autres: "Autres",
};

export default function Contacts() {
  const { user } = useUser();
  const isSyndic = user?.role === "syndic";
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [modal, setModal] = useState<null | { type: "contact"; item?: Contact }>(null);
  const [error, setError] = useState("");
  const [q, setQ] = useState("");

  async function load() {
    setContacts(await api.get<Contact[]>("/contacts"));
  }
  useEffect(() => { load().catch(() => {}); }, []);

  const filtres = useMemo(() => {
    const s = q.trim().toLowerCase();
    if (!s) return contacts;
    return contacts.filter(
      (c) =>
        c.nom.toLowerCase().includes(s) ||
        (TYPES[c.type] ?? c.type).toLowerCase().includes(s) ||
        (CATEGORIES[c.categorie] ?? c.categorie).toLowerCase().includes(s) ||
        c.email.toLowerCase().includes(s)
    );
  }, [contacts, q]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-800">Contacts</h1>
          <p className="text-sm text-slate-500">
            Entreprises, fournisseurs et artisans intervenant dans la copropriété
          </p>
        </div>
        {isSyndic && <Button onClick={() => setModal({ type: "contact" })}>+ Ajouter un contact</Button>}
      </div>

      {error && <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}

      <Card title={`Annuaire (${filtres.length})`} action={
        <Input placeholder="Rechercher…" value={q} onChange={(e) => setQ(e.target.value)} className="w-52" />
      }>
        {contacts.length === 0 ? (
          <Empty text="Aucun contact. Ajoutez les entreprises, fournisseurs et artisans (plombier, électricien, assureur…)." />
        ) : filtres.length === 0 ? (
          <Empty text="Aucun contact ne correspond à la recherche." />
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {filtres.map((c) => (
              <div key={c.id} className="rounded-lg border border-slate-200 p-3">
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="truncate font-medium text-slate-800">{c.nom}</p>
                    <div className="mt-1 flex flex-wrap gap-1.5">
                      <Badge color="indigo">{TYPES[c.type] ?? c.type}</Badge>
                      <Badge>{CATEGORIES[c.categorie] ?? c.categorie}</Badge>
                    </div>
                  </div>
                  {isSyndic && (
                    <Button variant="ghost" className="shrink-0 px-2 py-1 text-xs" onClick={() => setModal({ type: "contact", item: c })}>
                      Modifier
                    </Button>
                  )}
                </div>
                <div className="mt-2 space-y-0.5 text-xs text-slate-600">
                  {c.telephone && <p>📞 {c.telephone}</p>}
                  {c.email && <p>✉️ {c.email}</p>}
                  {c.adresse && <p>📍 {c.adresse}</p>}
                  {c.site_web && <p>🌐 {c.site_web}</p>}
                  {c.notes && <p className="text-slate-400">{c.notes}</p>}
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      {modal?.type === "contact" && (
        <ContactModal
          item={modal.item}
          onClose={() => setModal(null)}
          onSaved={() => { setModal(null); load(); }}
          onError={setError}
        />
      )}
    </div>
  );
}

function ContactModal({ item, onClose, onSaved, onError }: {
  item?: Contact; onClose: () => void; onSaved: () => void; onError: (e: string) => void;
}) {
  const [f, setF] = useState({
    nom: item?.nom ?? "",
    type: item?.type ?? "entreprise",
    categorie: item?.categorie ?? "autres",
    telephone: item?.telephone ?? "",
    email: item?.email ?? "",
    adresse: item?.adresse ?? "",
    site_web: item?.site_web ?? "",
    notes: item?.notes ?? "",
  });
  const set = (k: string, v: unknown) => setF((p) => ({ ...p, [k]: v }));

  async function save() {
    try {
      if (item) await api.put(`/contacts/${item.id}`, f);
      else await api.post("/contacts", f);
      onSaved();
    } catch (e) {
      onError(e instanceof Error ? e.message : "Erreur");
    }
  }

  return (
    <Modal open title={item ? `Modifier ${item.nom}` : "Nouveau contact"} onClose={onClose}>
      <div className="space-y-3">
        <Input label="Nom / raison sociale" value={f.nom} onChange={(e) => set("nom", e.target.value)} required />
        <div className="grid grid-cols-2 gap-3">
          <Select label="Type" value={f.type} onChange={(e) => set("type", e.target.value)}>
            {Object.entries(TYPES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </Select>
          <Select label="Catégorie" value={f.categorie} onChange={(e) => set("categorie", e.target.value)}>
            {Object.entries(CATEGORIES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </Select>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <Input label="Téléphone" value={f.telephone} onChange={(e) => set("telephone", e.target.value)} />
          <Input label="Email" type="email" value={f.email} onChange={(e) => set("email", e.target.value)} />
        </div>
        <Input label="Adresse" value={f.adresse} onChange={(e) => set("adresse", e.target.value)} />
        <Input label="Site web" value={f.site_web} onChange={(e) => set("site_web", e.target.value)} />
        <Input label="Notes" value={f.notes} onChange={(e) => set("notes", e.target.value)} />
        <div className="flex justify-end gap-2 pt-2">
          <Button variant="secondary" onClick={onClose}>Annuler</Button>
          <Button onClick={save}>Enregistrer</Button>
        </div>
      </div>
    </Modal>
  );
}
