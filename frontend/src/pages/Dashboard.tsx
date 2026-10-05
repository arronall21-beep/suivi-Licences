import { AlertOctagon, AlertTriangle, ArrowRight, Boxes, FileSpreadsheet, FileText, KeyRound, Wallet } from "lucide-react";
import type { ReactNode } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, Cell, LabelList, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { CATEGORY_LABELS, CATEGORY_SLUG, fmtDate, fmtMoney, fmtMoneyCompact, fmtNum } from "../format";
import { CHART, STATUS_META } from "../theme";
import { useFetch } from "../hooks";
import type { Dashboard as D, Status } from "../types";
import { Card, CardHeader, CriticalityBadge, DaysCell, EmptyState, InfoTip, PageHeader, PriorityBadge, Spinner, StatusBadge, Watermark } from "../components/ui";

function Kpi({ label, value, sub, icon, tone = "slate", to, small }: { label: string; value: ReactNode; sub?: ReactNode; icon: ReactNode; tone?: "slate" | "blue" | "orange" | "red"; to?: string; small?: boolean }) {
  const tones = { slate: "bg-slate-100 text-slate-600", blue: "bg-info-100 text-info-700", orange: "bg-caution-100 text-caution-700", red: "bg-danger-100 text-danger-700" };
  const body = (
    <div className="card flex h-full items-start justify-between gap-3 p-5 transition hover:shadow-md">
      <div className="min-w-0">
        <div className="text-sm font-medium text-slate-500">{label}</div>
        <div className={`mt-2 truncate font-semibold tabular-nums text-slate-900 ${small ? "text-xl" : "text-2xl xl:text-3xl"}`}>{value}</div>
        {sub && <div className="mt-1 text-xs text-slate-500">{sub}</div>}
      </div>
      <div className={`shrink-0 rounded-lg p-2.5 ${tones[tone]}`}>{icon}</div>
    </div>
  );
  return to ? <Link to={to}>{body}</Link> : body;
}

const STATUS_ORDER: Status[] = ["EXPIRE", "CRITIQUE", "ALERTE", "OK", "INCONNU"];

export default function Dashboard() {
  const { data: d, loading, error } = useFetch<D>("/dashboard");
  const navigate = useNavigate();
  if (loading && !d) return <Spinner />;
  if (error) return <div className="card p-6 text-danger-700">{error}</div>;
  if (!d) return null;

  if (d.kpis.total_assets === 0 && d.kpis.contracts === 0)
    return (
      <>
        <PageHeader title="Tableau de bord" />
        <div className="card">
          <EmptyState title="Aucune donnée pour le moment">
            <p className="mb-4">Importez le fichier Suivi_Licence.xlsx pour alimenter l'application.</p>
            <Link to="/import-export" className="btn-primary">
              <FileSpreadsheet className="h-4 w-4" /> Importer le fichier Excel
            </Link>
          </EmptyState>
        </div>
      </>
    );

  const k = d.kpis;
  const dl = d.deadlines;
  const { critical_days: cd, alert_days: ad } = d.thresholds;
  const statusData = d.status_by_category.map((r) => ({ ...r, name: r.label }));
  const deadlineBars = [
    { key: "EXPIRE", label: "Expirés", value: dl.expired },
    { key: "CRITIQUE", label: `≤ ${cd} jours`, value: dl.critical },
    { key: "ALERTE", label: `${cd + 1}–${ad} jours`, value: dl.warning },
    { key: "OK", label: `> ${ad} jours`, value: dl.ok },
    { key: "INCONNU", label: "Sans date", value: dl.unknown },
  ] as const;

  return (
    <>
      <div className="relative">
        <Watermark className="-top-8 right-0 h-28 w-28" />
        <PageHeader title="Tableau de bord" subtitle={`Situation au ${new Date().toLocaleDateString("fr-FR", { dateStyle: "long" })} — données issues de la base`} />
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Kpi label="Actifs suivis" value={fmtNum(k.total_assets)} icon={<Boxes className="h-5 w-5" />} tone="blue" to="/actifs"
          sub={`${k.licences} licences · ${k.certificats} certificats · ${k.materiels} matériels · ${k.applications} applications`} />
        <Kpi label="Licences utilisées" value={`${d.licenses.usage_rate.toLocaleString("fr-FR")} %`} icon={<KeyRound className="h-5 w-5" />} to="/actifs/licences"
          sub={`${fmtNum(d.licenses.used)} / ${fmtNum(d.licenses.total)} — ${fmtNum(d.licenses.available)} disponibles`} />
        <Kpi label={`Critiques (≤ ${cd} j)`} value={dl.critical} icon={<AlertTriangle className="h-5 w-5" />} tone="orange" to="/actifs?status=CRITIQUE"
          sub={`${dl.warning} à surveiller (≤ ${ad} j) · ${d.contract_deadlines.critical} contrat(s) critique(s)`} />
        <Kpi label="Expirés" value={dl.expired} icon={<AlertOctagon className="h-5 w-5" />} tone="red" to="/actifs?status=EXPIRE"
          sub={`${d.contract_deadlines.expired} contrat(s) expiré(s)`} />
      </div>

      <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Kpi label="Contrats" value={k.contracts} icon={<FileText className="h-5 w-5" />} to="/contrats" sub={`${k.vendors} fournisseurs`} />
        <Kpi label="Coût annuel des actifs" small value={<span title={fmtMoney(d.finance.annual_cost_total)}>{fmtMoneyCompact(d.finance.annual_cost_total)}</span>} icon={<Wallet className="h-5 w-5" />}
          sub={`Contrats : ${fmtMoneyCompact(d.finance.contracts_annual_total)} / an`} />
        <Kpi label="Budget estimé" small value={<span title={fmtMoney(d.finance.budget_estimated_total)}>{fmtMoneyCompact(d.finance.budget_estimated_total)}</span>} icon={<Wallet className="h-5 w-5" />} sub="Somme des budgets estimés des actifs" />
        <Kpi label="Budget renouvellement 12 mois" small value={<span title={fmtMoney(d.finance.renewal_budget_12m)}>{fmtMoneyCompact(d.finance.renewal_budget_12m)}</span>} icon={<Wallet className="h-5 w-5" />} sub="Échéances passées et à venir sous 12 mois" />
      </div>

      <div className="mt-6 grid grid-cols-1 gap-4 xl:grid-cols-2">
        <div className="card p-5">
          <h2 className="text-sm font-semibold text-slate-900">Répartition des actifs</h2>
          <p className="mb-3 text-xs text-slate-500">Nombre d'actifs par catégorie, ventilé par statut d'échéance</p>
          <div className="h-72">
            <ResponsiveContainer>
              <BarChart data={statusData} layout="vertical" margin={{ left: 10, right: 24 }} barCategoryGap={14}>
                <CartesianGrid horizontal={false} stroke={CHART.grid} />
                <XAxis type="number" allowDecimals={false} tick={{ fontSize: 12, fill: CHART.axis }} axisLine={false} tickLine={false} />
                <YAxis type="category" dataKey="name" width={95} tick={{ fontSize: 12, fill: CHART.label }} axisLine={false} tickLine={false} />
                <Tooltip cursor={{ fill: CHART.cursor }} />
                <Legend iconType="circle" wrapperStyle={{ fontSize: 12 }} />
                {STATUS_ORDER.map((s, i) => (
                  <Bar key={s} isAnimationActive={false} dataKey={s} stackId="a" name={STATUS_META[s].label} fill={STATUS_META[s].color} stroke={CHART.surface} strokeWidth={2}
                    radius={i === STATUS_ORDER.length - 1 ? [0, 4, 4, 0] : 0}
                    onClick={(row: { category?: string }) => row.category && navigate(`/actifs/${CATEGORY_SLUG[row.category as keyof typeof CATEGORY_SLUG]}?status=${s}`)}
                    className="cursor-pointer" />
                ))}
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
        <div className="card p-5">
          <h2 className="text-sm font-semibold text-slate-900">Échéances des actifs</h2>
          <p className="mb-3 text-xs text-slate-500">Nombre d'actifs par horizon d'expiration — cliquer pour filtrer</p>
          <div className="h-72">
            <ResponsiveContainer>
              <BarChart data={[...deadlineBars]} margin={{ top: 20, right: 10 }} barCategoryGap="25%">
                <CartesianGrid vertical={false} stroke={CHART.grid} />
                <XAxis dataKey="label" tick={{ fontSize: 12, fill: CHART.label }} axisLine={false} tickLine={false} />
                <YAxis allowDecimals={false} tick={{ fontSize: 12, fill: CHART.axis }} axisLine={false} tickLine={false} />
                <Tooltip cursor={{ fill: CHART.cursor }} formatter={(v: number) => [v, "Actifs"]} />
                <Bar isAnimationActive={false} dataKey="value" radius={[4, 4, 0, 0]} className="cursor-pointer" onClick={(row: { key?: string }) => navigate(`/actifs?status=${row.key}`)}>
                  {deadlineBars.map((b) => (
                    <Cell key={b.key} fill={STATUS_META[b.key].color} />
                  ))}
                  <LabelList dataKey="value" position="top" style={{ fontSize: 12, fill: CHART.label, fontWeight: 600 }} />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <Card className="mt-6">
        <CardHeader
          title={
            <span className="inline-flex items-center gap-1.5">
              Top des risques
              <InfoTip text="Score = criticité (1 à 4) × urgence (alerte 2, critique 4, expiré 5) + impact (licence très utilisée, ou actif rattaché à un contrat). Survolez une ligne pour le détail." />
            </span>
          }
          subtitle="Actifs les plus urgents à traiter, hors échéances confortables"
        />
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200">
            <thead className="table-head">
              <tr>
                <th className="th">Actif</th>
                <th className="th">Catégorie</th>
                <th className="th">Criticité</th>
                <th className="th">Échéance</th>
                <th className="th">Jours restants</th>
                <th className="th">Statut</th>
                <th className="th">Responsable</th>
                <th className="th text-right">Score</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {d.top_risks.map((r) => (
                <tr key={r.id} className="cursor-pointer hover:bg-slate-50" title={r.reasons.join(" · ")} onClick={() => navigate(`/actifs/fiche/${r.id}`)}>
                  <td className="td">
                    <div className="font-medium text-slate-900">{r.name}</div>
                    <div className="text-xs text-slate-500">{r.reference}</div>
                  </td>
                  <td className="td">{CATEGORY_LABELS[r.category]}</td>
                  <td className="td"><CriticalityBadge value={r.criticality} /></td>
                  <td className="td">{fmtDate(r.end_date)}</td>
                  <td className="td"><DaysCell days={r.days_remaining} /></td>
                  <td className="td"><StatusBadge status={r.status} /></td>
                  <td className="td">{r.owner ?? "—"}</td>
                  <td className="td text-right font-semibold tabular-nums text-slate-900">{r.score}</td>
                </tr>
              ))}
              {d.top_risks.length === 0 && (
                <tr><td colSpan={8}><EmptyState title="Aucun actif à risque" /></td></tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>

      <div className="card mt-6">
        <div className="flex items-center justify-between border-b border-slate-200 px-5 py-4">
          <div>
            <h2 className="text-sm font-semibold text-slate-900">Planning des prochains renouvellements</h2>
            <p className="text-xs text-slate-500">Éléments échus ou arrivant à échéance dans les 6 mois</p>
          </div>
          <Link to="/renouvellements" className="btn-secondary">
            Planning complet <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200">
            <thead className="bg-slate-50">
              <tr>
                <th className="th">Actif / Contrat</th>
                <th className="th">Type</th>
                <th className="th">Échéance</th>
                <th className="th">Jours restants</th>
                <th className="th">Priorité</th>
                <th className="th">Responsable</th>
                <th className="th">Statut</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {d.upcoming_renewals.map((r) => (
                <tr key={`${r.kind}-${r.id}`} className="cursor-pointer hover:bg-slate-50"
                  onClick={() => navigate(r.kind === "ASSET" ? `/actifs/fiche/${r.id}` : `/contrats?focus=${r.id}`)}>
                  <td className="td">
                    <div className="font-medium text-slate-900">{r.name}</div>
                    <div className="text-xs text-slate-500">{r.reference}{r.vendor_name ? ` · ${r.vendor_name}` : ""}</div>
                  </td>
                  <td className="td">{CATEGORY_LABELS[r.type]}</td>
                  <td className="td">{fmtDate(r.end_date)}</td>
                  <td className="td"><DaysCell days={r.days_remaining} /></td>
                  <td className="td"><PriorityBadge value={r.priority} /></td>
                  <td className="td">{r.owner ?? "—"}</td>
                  <td className="td"><StatusBadge status={r.status} /></td>
                </tr>
              ))}
              {d.upcoming_renewals.length === 0 && (
                <tr><td colSpan={7}><EmptyState title="Aucun renouvellement dans les 6 prochains mois" /></td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}
