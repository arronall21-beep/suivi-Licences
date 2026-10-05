import { useState, type FormEvent, type ReactNode } from "react";
import { api } from "../api";
import { CATEGORY_LABELS, CERT_TYPES, CURRENCY, CONTRACT_TYPES, CRITICALITIES, ENVIRONMENTS, LICENSE_TYPES } from "../format";
import { useReferenceData } from "../hooks";
import type { Asset, Assignment, Category, Contract, Vendor } from "../types";
import { Button, Field, FormError, useToast } from "./ui";

type Values = Record<string, string>;

function toValues(obj: object | null | undefined, keys: string[]): Values {
  const o = (obj ?? {}) as Record<string, unknown>;
  return Object.fromEntries(keys.map((k) => [k, o[k] === null || o[k] === undefined ? "" : String(o[k])]));
}

function toPayload(v: Values, numeric: string[]) {
  const out: Record<string, unknown> = {};
  Object.entries(v).forEach(([k, val]) => {
    const t = val.trim();
    out[k] = t === "" ? null : numeric.includes(k) ? Number(t) : t;
  });
  return out;
}

function useForm(initial: Values) {
  const [values, setValues] = useState(initial);
  const bind = (k: string) => ({
    value: values[k] ?? "",
    onChange: (e: { target: { value: string } }) => setValues((v) => ({ ...v, [k]: e.target.value })),
  });
  return { values, bind, setValues };
}

function FormShell({ onSubmit, onCancel, saving, error, children }: { onSubmit: (e: FormEvent) => void; onCancel: () => void; saving: boolean; error: string | null; children: ReactNode }) {
  return (
    <form onSubmit={onSubmit} className="space-y-5">
      {children}
      <FormError message={error} />
      <div className="flex justify-end gap-2 border-t border-slate-200 pt-4">
        <Button type="button" variant="secondary" onClick={onCancel}>
          Annuler
        </Button>
        <Button type="submit" loading={saving}>
          {saving ? "Enregistrement…" : "Enregistrer"}
        </Button>
      </div>
    </form>
  );
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <fieldset>
      <legend className="mb-3 text-xs font-semibold uppercase tracking-wide text-brand-700">{title}</legend>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">{children}</div>
    </fieldset>
  );
}

function Select({ options, placeholder = "—", ...props }: { options: (string | { value: string | number; label: string })[]; placeholder?: string; value: string; onChange: (e: { target: { value: string } }) => void }) {
  return (
    <select className="input" {...props}>
      <option value="">{placeholder}</option>
      {options.map((o) =>
        typeof o === "string" ? (
          <option key={o} value={o}>
            {o}
          </option>
        ) : (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ),
      )}
    </select>
  );
}

// Choix libre avec suggestions (valeurs Excel non standard conservées)
function Combo({ id, options, ...props }: { id: string; options: string[]; value: string; onChange: (e: { target: { value: string } }) => void }) {
  return (
    <>
      <input className="input" list={id} {...props} />
      <datalist id={id}>
        {options.map((o) => (
          <option key={o} value={o} />
        ))}
      </datalist>
    </>
  );
}

const ASSET_KEYS = [
  "reference", "category", "name", "vendor_id", "contract_id", "internal_owner", "user_department", "start_date", "end_date",
  "criticality", "annual_cost", "budget_estimated", "action_plan", "observation", "lic_type", "license_key", "total_quantity",
  "cert_type", "authority", "server_app_target", "environment", "brand", "model", "serial_number", "site_location",
  "warranty_end_date", "support_end_date", "support_contract_type", "business_owner", "hosting_env", "service_provider", "sla_level",
];

export function AssetForm({ asset, category, onSaved, onCancel }: { asset?: Asset | null; category?: Category; onSaved: (a: Asset) => void; onCancel: () => void }) {
  const toast = useToast();
  const { vendors, contracts } = useReferenceData();
  const { values, bind } = useForm(toValues(asset ?? { category: category ?? "LICENCE" }, ASSET_KEYS));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const cat = values.category as Category;

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const body = toPayload(values, ["vendor_id", "contract_id", "annual_cost", "budget_estimated", "total_quantity"]);
      delete body.reference; // générée côté serveur à la création, conservée à la modification
      const saved = asset ? await api.put<Asset>(`/assets/${asset.id}`, body) : await api.post<Asset>("/assets", body);
      toast("success", asset ? "Actif mis à jour" : "Actif créé");
      onSaved(saved);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <FormShell onSubmit={submit} onCancel={onCancel} saving={saving} error={error}>
      <Section title="Informations générales">
        <Field label="Catégorie *">
          <select className="input" {...bind("category")} disabled={!!asset}>
            {(["LICENCE", "CERTIFICAT", "MATERIEL", "APPLICATION"] as Category[]).map((c) => (
              <option key={c} value={c}>
                {CATEGORY_LABELS[c]}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Référence" hint={asset ? "Non modifiable" : "Référence générée automatiquement"}>
          <input className="input" disabled readOnly value={asset ? asset.reference : "Générée à l'enregistrement"} />
        </Field>
        <Field label="Nom *">
          <input className="input" required {...bind("name")} />
        </Field>
        <Field label="Fournisseur">
          <Select options={vendors.map((v) => ({ value: v.id, label: v.name }))} {...bind("vendor_id")} />
        </Field>
        <Field label="Contrat">
          <Select options={contracts.map((c) => ({ value: c.id, label: `${c.reference}${c.vendor_name ? " — " + c.vendor_name : ""}` }))} {...bind("contract_id")} />
        </Field>
        <Field label="Criticité">
          <Combo id="crit" options={CRITICALITIES} {...bind("criticality")} />
        </Field>
        <Field label="Responsable interne">
          <input className="input" {...bind("internal_owner")} />
        </Field>
        <Field label="Direction utilisatrice">
          <input className="input" {...bind("user_department")} />
        </Field>
      </Section>

      {cat === "LICENCE" && (
        <Section title="Licence">
          <Field label="Type de licence">
            <Combo id="lictype" options={LICENSE_TYPES} {...bind("lic_type")} />
          </Field>
          <Field label="Quantité totale">
            <input className="input" type="number" min={0} {...bind("total_quantity")} />
          </Field>
          <Field label="Clé de licence">
            <input className="input" {...bind("license_key")} />
          </Field>
        </Section>
      )}
      {cat === "CERTIFICAT" && (
        <Section title="Certificat">
          <Field label="Type de certificat">
            <Combo id="certtype" options={CERT_TYPES} {...bind("cert_type")} />
          </Field>
          <Field label="Autorité de certification">
            <input className="input" {...bind("authority")} />
          </Field>
          <Field label="Serveur / application cible">
            <input className="input" {...bind("server_app_target")} />
          </Field>
          <Field label="Environnement">
            <Combo id="env" options={ENVIRONMENTS} {...bind("environment")} />
          </Field>
        </Section>
      )}
      {cat === "MATERIEL" && (
        <Section title="Matériel">
          <Field label="Marque">
            <input className="input" {...bind("brand")} />
          </Field>
          <Field label="Modèle">
            <input className="input" {...bind("model")} />
          </Field>
          <Field label="Numéro de série">
            <input className="input" {...bind("serial_number")} />
          </Field>
          <Field label="Site / localisation">
            <input className="input" {...bind("site_location")} />
          </Field>
          <Field label="Fin de garantie">
            <input className="input" type="date" {...bind("warranty_end_date")} />
          </Field>
          <Field label="Fin de support">
            <input className="input" type="date" {...bind("support_end_date")} />
          </Field>
          <Field label="Type de contrat support">
            <input className="input" {...bind("support_contract_type")} />
          </Field>
        </Section>
      )}
      {cat === "APPLICATION" && (
        <Section title="Application">
          <Field label="Propriétaire métier">
            <input className="input" {...bind("business_owner")} />
          </Field>
          <Field label="Hébergement">
            <input className="input" {...bind("hosting_env")} />
          </Field>
          <Field label="Prestataire">
            <input className="input" {...bind("service_provider")} />
          </Field>
          <Field label="Niveau de SLA">
            <input className="input" {...bind("sla_level")} />
          </Field>
        </Section>
      )}

      <Section title="Dates et coûts">
        <Field label="Date de début">
          <input className="input" type="date" {...bind("start_date")} />
        </Field>
        <Field label={cat === "MATERIEL" ? "Date de fin de contrat" : "Date d'échéance"}>
          <input className="input" type="date" {...bind("end_date")} />
        </Field>
        <div />
        <Field label="Coût annuel">
          <input className="input" type="number" min={0} step="0.01" {...bind("annual_cost")} />
        </Field>
        <Field label="Budget estimé">
          <input className="input" type="number" min={0} step="0.01" {...bind("budget_estimated")} />
        </Field>
      </Section>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <Field label="Plan d'action">
          <textarea className="input" rows={3} {...bind("action_plan")} />
        </Field>
        <Field label="Observations">
          <textarea className="input" rows={3} {...bind("observation")} />
        </Field>
      </div>
    </FormShell>
  );
}

const CONTRACT_KEYS = ["reference", "market_ref", "vendor_id", "type", "scope", "internal_owner", "start_date", "end_date", "notice_period_days", "annual_amount", "currency", "status", "attachment_url"];

export function ContractForm({ contract, onSaved, onCancel }: { contract?: Contract | null; onSaved: () => void; onCancel: () => void }) {
  const toast = useToast();
  const { vendors } = useReferenceData();
  const { values, bind } = useForm(toValues(contract ?? { currency: CURRENCY, status: "Actif" }, CONTRACT_KEYS));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const body = toPayload(values, ["vendor_id", "notice_period_days", "annual_amount"]);
      delete body.reference; // générée côté serveur à la création, conservée à la modification
      if (contract) await api.put(`/contracts/${contract.id}`, body);
      else await api.post("/contracts", body);
      toast("success", contract ? "Contrat mis à jour" : "Contrat créé");
      onSaved();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSaving(false);
    }
  };
  return (
    <FormShell onSubmit={submit} onCancel={onCancel} saving={saving} error={error}>
      <Section title="Contrat">
        <Field label="Référence" hint={contract ? "Non modifiable" : "Référence générée automatiquement"}>
          <input className="input" disabled readOnly value={contract ? contract.reference : "Générée à l'enregistrement"} />
        </Field>
        <Field label="Référence marché">
          <input className="input" {...bind("market_ref")} />
        </Field>
        <Field label="Fournisseur">
          <Select options={vendors.map((v: Vendor) => ({ value: v.id, label: v.name }))} {...bind("vendor_id")} />
        </Field>
        <Field label="Type">
          <Combo id="ctype" options={CONTRACT_TYPES} {...bind("type")} />
        </Field>
        <Field label="Responsable interne">
          <input className="input" {...bind("internal_owner")} />
        </Field>
        <Field label="Statut contractuel">
          <Combo id="cstatus" options={["Actif", "En renouvellement", "Résilié", "À compléter"]} {...bind("status")} />
        </Field>
        <Field label="Périmètre" className="sm:col-span-2 lg:col-span-3">
          <input className="input" {...bind("scope")} />
        </Field>
      </Section>
      <Section title="Échéances et montant">
        <Field label="Date de début">
          <input className="input" type="date" {...bind("start_date")} />
        </Field>
        <Field label="Date de fin">
          <input className="input" type="date" {...bind("end_date")} />
        </Field>
        <Field label="Préavis (jours)">
          <input className="input" type="number" min={0} {...bind("notice_period_days")} />
        </Field>
        <Field label="Montant annuel">
          <input className="input" type="number" min={0} step="0.01" {...bind("annual_amount")} />
        </Field>
        <Field label="Devise">
          <input className="input" {...bind("currency")} />
        </Field>
        <Field label="Lien pièce jointe">
          <input className="input" type="url" {...bind("attachment_url")} />
        </Field>
      </Section>
    </FormShell>
  );
}

export function VendorForm({ vendor, onSaved, onCancel }: { vendor?: Vendor | null; onSaved: () => void; onCancel: () => void }) {
  const toast = useToast();
  const { values, bind } = useForm(toValues(vendor, ["name", "contact_person", "email_support", "phone", "website"]));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const body = toPayload(values, []);
      if (vendor) await api.put(`/vendors/${vendor.id}`, body);
      else await api.post("/vendors", body);
      toast("success", vendor ? "Fournisseur mis à jour" : "Fournisseur créé");
      onSaved();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSaving(false);
    }
  };
  return (
    <FormShell onSubmit={submit} onCancel={onCancel} saving={saving} error={error}>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <Field label="Référence" hint={vendor ? "Non modifiable" : "Référence générée automatiquement"}>
          <input className="input" disabled readOnly value={vendor?.reference ?? "Générée à l'enregistrement"} />
        </Field>
        <Field label="Nom *">
          <input className="input" required {...bind("name")} />
        </Field>
        <Field label="Contact">
          <input className="input" {...bind("contact_person")} />
        </Field>
        <Field label="Email support">
          <input className="input" type="email" {...bind("email_support")} />
        </Field>
        <Field label="Téléphone">
          <input className="input" {...bind("phone")} />
        </Field>
        <Field label="Site web">
          <input className="input" {...bind("website")} />
        </Field>
      </div>
    </FormShell>
  );
}

export function AssignmentForm({ assignment, licences, fixedAssetId, onSaved, onCancel }: { assignment?: Assignment | null; licences?: Asset[]; fixedAssetId?: number; onSaved: () => void; onCancel: () => void }) {
  const toast = useToast();
  const { values, bind } = useForm(
    toValues(assignment ?? { asset_id: fixedAssetId ?? "", quantity: 1, assigned_date: new Date().toISOString().slice(0, 10) }, [
      "asset_id", "assigned_to_user", "assigned_to_device", "assigned_to_department", "assigned_date", "quantity", "notes",
    ]),
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const selected = licences?.find((l) => String(l.id) === values.asset_id);
  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const body = toPayload(values, ["asset_id", "quantity"]);
      if (assignment) await api.put(`/assignments/${assignment.id}`, body);
      else await api.post("/assignments", body);
      toast("success", assignment ? "Affectation mise à jour" : "Licence affectée");
      onSaved();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSaving(false);
    }
  };
  return (
    <FormShell onSubmit={submit} onCancel={onCancel} saving={saving} error={error}>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {!fixedAssetId && (
          <Field label="Licence *" className="sm:col-span-2">
            <select className="input" required {...bind("asset_id")}>
              <option value="">Choisir une licence…</option>
              {licences?.map((l) => (
                <option key={l.id} value={l.id}>
                  {l.reference} — {l.name} ({l.available_quantity ?? 0} dispo.)
                </option>
              ))}
            </select>
          </Field>
        )}
        {selected && (
          <div className="rounded-md bg-brand-50 px-3 py-2 text-sm text-brand-800 sm:col-span-2">
            {selected.assigned_quantity} / {selected.total_quantity ?? 0} affectées — <b>{selected.available_quantity ?? 0} disponible(s)</b>
          </div>
        )}
        <Field label="Utilisateur">
          <input className="input" {...bind("assigned_to_user")} placeholder="ex. j.dupont" />
        </Field>
        <Field label="Poste / équipement">
          <input className="input" {...bind("assigned_to_device")} placeholder="ex. PC-DSI-042" />
        </Field>
        <Field label="Direction">
          <input className="input" {...bind("assigned_to_department")} />
        </Field>
        <Field label="Quantité *">
          <input className="input" type="number" min={1} required {...bind("quantity")} />
        </Field>
        <Field label="Date d'affectation">
          <input className="input" type="date" {...bind("assigned_date")} />
        </Field>
        <Field label="Notes" className="sm:col-span-2">
          <textarea className="input" rows={2} {...bind("notes")} />
        </Field>
      </div>
    </FormShell>
  );
}
