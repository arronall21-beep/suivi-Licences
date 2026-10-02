import { AlertTriangle, CheckCircle2, Download, FileSpreadsheet, Upload, XCircle } from "lucide-react";
import { useRef, useState, type DragEvent } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";
import { PageHeader, useToast } from "../components/ui";
import { fmtDateTime } from "../format";
import { useFetch } from "../hooks";
import type { ImportReport } from "../types";

interface HistoryRow {
  id: number;
  filename: string;
  rows_analyzed: number;
  rows_imported: number;
  rows_skipped: number;
  warnings_count: number;
  errors_count: number;
  imported_by: string | null;
  created_at: string;
}

function Stat({ label, value, tone }: { label: string; value: number; tone: string }) {
  return (
    <div className="rounded-lg border border-slate-200 p-4">
      <div className="text-xs font-medium text-slate-500">{label}</div>
      <div className={`mt-1 text-2xl font-semibold tabular-nums ${tone}`}>{value}</div>
    </div>
  );
}

function Report({ r }: { r: ImportReport }) {
  return (
    <div className="card mt-6">
      <div className="flex items-center gap-2 border-b border-slate-200 px-5 py-3">
        {r.errors_count ? <AlertTriangle className="h-5 w-5 text-amber-500" /> : <CheckCircle2 className="h-5 w-5 text-emerald-600" />}
        <h2 className="text-sm font-semibold text-slate-900">Rapport d'import — {r.filename}</h2>
        <Link to="/" className="btn-secondary ml-auto py-1.5">Voir le dashboard</Link>
      </div>
      <div className="p-5">
        <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
          <Stat label="Lignes analysées" value={r.rows_analyzed} tone="text-slate-900" />
          <Stat label="Lignes importées" value={r.rows_imported} tone="text-emerald-700" />
          <Stat label="Lignes ignorées" value={r.rows_skipped} tone="text-slate-700" />
          <Stat label="Avertissements" value={r.warnings_count} tone="text-amber-600" />
          <Stat label="Erreurs" value={r.errors_count} tone="text-red-700" />
        </div>
        <p className="mt-3 text-sm text-slate-600">
          {r.created} création(s), {r.updated} mise(s) à jour (UPSERT par référence), {r.vendors_created} fournisseur(s) créé(s).
        </p>
        <table className="mt-4 min-w-full divide-y divide-slate-200 text-sm">
          <thead className="bg-slate-50"><tr><th className="th">Onglet</th><th className="th text-right">Analysées</th><th className="th text-right">Créées</th><th className="th text-right">Mises à jour</th><th className="th text-right">Ignorées</th><th className="th">Remarque</th></tr></thead>
          <tbody className="divide-y divide-slate-100">
            {r.sheets.map((s) => (
              <tr key={s.sheet}>
                <td className="td font-medium">{s.sheet}</td>
                <td className="td text-right">{s.rows_analyzed}</td>
                <td className="td text-right">{s.created}</td>
                <td className="td text-right">{s.updated}</td>
                <td className="td text-right">{s.skipped}</td>
                <td className="td text-slate-500">{s.note ?? ""}</td>
              </tr>
            ))}
            {r.missing_sheets.map((s) => (
              <tr key={s}><td className="td font-medium text-slate-400">{s}</td><td colSpan={5} className="td text-amber-700">Onglet manquant dans le fichier</td></tr>
            ))}
          </tbody>
        </table>
        {[...r.errors.map((e) => ({ ...e, kind: "error" })), ...r.warnings.map((w) => ({ ...w, kind: "warn" }))].length > 0 && (
          <div className="mt-5">
            <h3 className="mb-2 text-sm font-semibold text-slate-900">Anomalies détectées</h3>
            <ul className="max-h-80 divide-y divide-slate-100 overflow-y-auto rounded-lg border border-slate-200">
              {r.errors.map((e, i) => (
                <li key={`e${i}`} className="flex gap-2 px-3 py-2 text-sm"><XCircle className="mt-0.5 h-4 w-4 shrink-0 text-red-600" /><span className="text-slate-500">{e.sheet}{e.row ? ` · ligne ${e.row}` : ""}</span><span className="text-slate-800">{e.message}</span></li>
              ))}
              {r.warnings.map((w, i) => (
                <li key={`w${i}`} className="flex gap-2 px-3 py-2 text-sm"><AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-500" /><span className="shrink-0 text-slate-500">{w.sheet}{w.row ? ` · ligne ${w.row}` : ""}</span><span className="text-slate-800">{w.message}</span></li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}

export default function ImportExport() {
  const { isAdmin } = useAuth();
  const toast = useToast();
  const input = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [report, setReport] = useState<ImportReport | null>(null);
  const [drag, setDrag] = useState(false);
  const [exporting, setExporting] = useState(false);
  const history = useFetch<HistoryRow[]>("/import/history");

  const doImport = async () => {
    if (!file) return;
    setBusy(true);
    setReport(null);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const r = await api.post<ImportReport>("/import/excel", fd);
      setReport(r);
      toast("success", `${r.rows_imported} ligne(s) importée(s)`);
      history.reload();
    } catch (e) {
      toast("error", (e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  const doExport = async () => {
    setExporting(true);
    try {
      await api.download("/export/excel", "Suivi_Licence_export.xlsx");
    } catch (e) {
      toast("error", (e as Error).message);
    } finally {
      setExporting(false);
    }
  };
  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    setDrag(false);
    const f = e.dataTransfer.files[0];
    if (f) setFile(f);
  };

  return (
    <>
      <PageHeader title="Import / Export Excel" subtitle="Le fichier Suivi_Licence.xlsx est la source métier de référence" />
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="card p-5">
          <h2 className="flex items-center gap-2 text-sm font-semibold text-slate-900"><Upload className="h-4 w-4" /> Importer</h2>
          <p className="mt-1 text-sm text-slate-500">
            Onglets lus : Licences_Logicielles, Certificats, Materiels, Applications, Contrats_Fournisseurs. Les enregistrements existants sont mis à jour par référence (aucune suppression).
          </p>
          {isAdmin ? (
            <>
              <div
                onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
                onDragLeave={() => setDrag(false)}
                onDrop={onDrop}
                onClick={() => input.current?.click()}
                className={`mt-4 flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed px-6 py-10 text-center transition ${drag ? "border-blue-500 bg-blue-50" : "border-slate-300 hover:border-blue-400 hover:bg-slate-50"}`}
              >
                <FileSpreadsheet className="h-10 w-10 text-emerald-600" />
                <div className="mt-2 text-sm font-medium text-slate-800">{file ? file.name : "Glisser le fichier .xlsx ici ou cliquer pour choisir"}</div>
                <div className="text-xs text-slate-500">{file ? `${(file.size / 1024).toFixed(0)} Ko` : "Taille maximale : 10 Mo"}</div>
                <input ref={input} type="file" accept=".xlsx,.xlsm" className="hidden" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
              </div>
              <button className="btn-primary mt-4 w-full" disabled={!file || busy} onClick={doImport}>{busy ? "Import en cours…" : "Lancer l'import"}</button>
            </>
          ) : (
            <p className="mt-4 rounded-md bg-slate-50 p-3 text-sm text-slate-600">L'import est réservé aux administrateurs.</p>
          )}
        </div>
        <div className="card p-5">
          <h2 className="flex items-center gap-2 text-sm font-semibold text-slate-900"><Download className="h-4 w-4" /> Exporter</h2>
          <p className="mt-1 text-sm text-slate-500">
            Génère un classeur au format de Suivi_Licence.xlsx à partir de la base : 7 onglets métier, dates au format JJ/MM/AAAA, statuts et jours restants recalculés, planning et dashboard à jour.
          </p>
          <ul className="mt-4 grid grid-cols-2 gap-2 text-sm text-slate-700">
            {["Licences_Logicielles", "Certificats", "Materiels", "Applications", "Contrats_Fournisseurs", "Planning_Renouvellement", "Dashboard"].map((s) => (
              <li key={s} className="flex items-center gap-2"><FileSpreadsheet className="h-4 w-4 text-emerald-600" />{s}</li>
            ))}
          </ul>
          <button className="btn-primary mt-6 w-full" onClick={doExport} disabled={exporting}>
            <Download className="h-4 w-4" /> {exporting ? "Génération…" : "Télécharger l'export Excel"}
          </button>
        </div>
      </div>

      {report && <Report r={report} />}

      <div className="card mt-6 overflow-hidden">
        <div className="border-b border-slate-200 px-5 py-3 text-sm font-semibold text-slate-900">Historique des imports</div>
        <table className="min-w-full divide-y divide-slate-200">
          <thead className="bg-slate-50"><tr><th className="th">Date</th><th className="th">Fichier</th><th className="th">Par</th><th className="th text-right">Analysées</th><th className="th text-right">Importées</th><th className="th text-right">Ignorées</th><th className="th text-right">Avert.</th><th className="th text-right">Erreurs</th><th className="th" /></tr></thead>
          <tbody className="divide-y divide-slate-100">
            {history.data?.map((h) => (
              <tr key={h.id} className="hover:bg-slate-50">
                <td className="td">{fmtDateTime(h.created_at)}</td>
                <td className="td">{h.filename}</td>
                <td className="td">{h.imported_by ?? "—"}</td>
                <td className="td text-right">{h.rows_analyzed}</td>
                <td className="td text-right text-emerald-700">{h.rows_imported}</td>
                <td className="td text-right">{h.rows_skipped}</td>
                <td className="td text-right text-amber-600">{h.warnings_count}</td>
                <td className="td text-right text-red-700">{h.errors_count}</td>
                <td className="td text-right"><button className="btn-ghost text-blue-700" onClick={async () => setReport(await api.get<ImportReport>(`/import/history/${h.id}`))}>Rapport</button></td>
              </tr>
            ))}
            {history.data?.length === 0 && <tr><td colSpan={9} className="td text-center text-slate-500">Aucun import réalisé</td></tr>}
          </tbody>
        </table>
      </div>
    </>
  );
}
