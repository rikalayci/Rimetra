import { ArrowLeft } from "lucide-react";
import { t } from "../lib/i18n";
import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { ErrorBox, Spinner, StatusPill } from "../components/ui";
import { catLabel, fmtDate, fmtNum, isOut, refText, valueText } from "../lib/format";
import { useApi } from "../lib/hooks";

export default function Compare() {
  const [sp] = useSearchParams();
  const a = sp.get("a");
  const b = sp.get("b");
  const { data, error, loading } = useApi<any>(a && b ? `/api/app/compare?a=${a}&b=${b}` : null);
  const [onlyBoth, setOnlyBoth] = useState(false);
  const [onlyChanged, setOnlyChanged] = useState(false);
  if (!a || !b) return <ErrorBox error={{ message: t("Karşılaştırmak için iki rapor seçin.") }} />;
  if (loading && !data) return <Spinner />;
  if (error) return <ErrorBox error={error} />;
  if (!data) return null;
  let lines = data.lines as any[];
  if (onlyBoth) lines = lines.filter((l) => l.a && l.b);
  if (onlyChanged) lines = lines.filter((l) => l.a && l.b && (l.a.flag_computed !== l.b.flag_computed || (l.diff_pct !== null && Math.abs(l.diff_pct) >= 10)));
  let lastCat = "";

  const head = (h: any, label: string) => (
    <div className="card flex-1 p-4">
      <div className="text-xs font-bold uppercase text-muted">{label}</div>
      <div className="text-xl font-extrabold">{fmtDate(h.report_date)}</div>
      <div className="truncate text-sm text-muted">{h.facility ?? "—"}</div>
      <div className="mt-1 text-xs text-muted">{h.result_count} {" "}{t("değer ·")}{" "}{h.out_of_range} {" "}{t("referans dışı")}</div>
    </div>
  );

  return (
    <div className="space-y-5">
      <Link to={`/uye/${data.a.member_id}?sekme=raporlar`} className="btn-ghost btn-sm"><ArrowLeft size={15} /> {" "}{t("Raporlar")}</Link>
      <h1 className="text-[28px] font-extrabold">{t("Rapor karşılaştırma")}</h1>
      <div className="flex flex-col gap-3 sm:flex-row">{head(data.a, t("Önceki"))}{head(data.b, t("Sonraki"))}</div>
      <div className="flex flex-wrap gap-4 text-sm">
        <label className="flex items-center gap-2"><input type="checkbox" checked={onlyBoth} onChange={(e) => setOnlyBoth(e.target.checked)} /> {" "}{t("Yalnızca iki raporda da olanlar")}</label>
        <label className="flex items-center gap-2"><input type="checkbox" checked={onlyChanged} onChange={(e) => setOnlyChanged(e.target.checked)} /> {" "}{t("Durumu değişen veya ≥%10 farklı")}</label>
      </div>
      <div className="card overflow-x-auto">
        <table className="table-clean w-full min-w-[820px]">
          <thead className="bg-surface2"><tr><th>{t("Test")}</th><th>{t("Önceki")}</th><th>{t("Sonraki")}</th><th>{t("Fark")}</th><th>{t("Referans (son)")}</th></tr></thead>
          <tbody>
            {lines.map((l) => {
              const showCat = l.category !== lastCat;
              lastCat = l.category;
              const r = l.b ?? l.a;
              return [
                showCat && (
                  <tr key={l.key + "-cat"}><td colSpan={5} className="bg-surface2/60 text-xs font-bold uppercase tracking-wide text-muted">{catLabel(l.category)}</td></tr>
                ),
                <tr key={l.key}>
                  <td className="font-semibold">{l.display_name}</td>
                  <td className={l.a && isOut(l.a.flag_computed) ? "text-bad" : ""}>
                    {l.a ? <div className="flex items-center gap-2"><b>{valueText(l.a)}</b><span className="text-xs text-muted">{l.a.unit}</span><StatusPill flag={l.a.flag_computed} small /></div> : <span className="text-muted">—</span>}
                  </td>
                  <td className={l.b && isOut(l.b.flag_computed) ? "text-bad" : ""}>
                    {l.b ? <div className="flex items-center gap-2"><b>{valueText(l.b)}</b><span className="text-xs text-muted">{l.b.unit}</span><StatusPill flag={l.b.flag_computed} small /></div> : <span className="text-muted">—</span>}
                  </td>
                  <td className="whitespace-nowrap font-semibold">
                    {l.diff !== null ? (
                      <span>{l.diff > 0 ? "↑ +" : l.diff < 0 ? "↓ " : "→ "}{fmtNum(l.diff)}{l.diff_pct !== null && <span className="ml-1 text-xs text-muted">({l.diff_pct > 0 ? "+" : ""}{fmtNum(l.diff_pct, 1)}%)</span>}</span>
                    ) : l.a && l.b && l.a.flag_computed !== l.b.flag_computed ? <span className="text-warn">{t("durum değişti")}</span> : <span className="text-muted">—</span>}
                  </td>
                  <td className="text-muted">{refText(r)}</td>
                </tr>,
              ];
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
