import { Building2, ChevronDown, FileText, GitCompare, Layers } from "lucide-react";
import { t } from "../lib/i18n";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import type { ReportHeader } from "../lib/api";
import { useAuth } from "../lib/auth";
import { fmtDate } from "../lib/format";
import { useApi } from "../lib/hooks";
import { ReportTable } from "./ReportTable";
import { Empty, Spinner } from "./ui";

export function ReportsTab({ memberId }: { memberId: string }) {
  const { me } = useAuth();
  const [showDeleted, setShowDeleted] = useState(false);
  const { data, loading, reload } = useApi<{ items: ReportHeader[] }>(
    `/api/app/members/${memberId}/reports${showDeleted ? "?include_deleted=true" : ""}`,
  );
  const [open, setOpen] = useState<string | null>(null);
  const [sel, setSel] = useState<string[]>([]);
  const nav = useNavigate();

  if (loading && !data) return <Spinner />;
  const items = data?.items ?? [];
  const toggle = (id: string) => setSel((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s.slice(-1), id]));

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <div className="text-sm text-muted">{items.filter((r) => !r.deleted_at).length} {" "}{t("rapor · karşılaştırmak için iki rapor seçin")}</div>
        <button className="btn-primary btn-sm ml-auto" disabled={sel.length !== 2} onClick={() => nav(`/karsilastir?a=${sel[0]}&b=${sel[1]}`)}>
          <GitCompare size={15} /> {" "}{t("Karşılaştır")}{" "}{sel.length > 0 && `(${sel.length}/2)`}
        </button>
        {me?.role === "master" && (
          <label className="flex items-center gap-2 text-xs text-muted">
            <input type="checkbox" checked={showDeleted} onChange={(e) => setShowDeleted(e.target.checked)} /> {" "}{t("Silinenleri göster")}</label>
        )}
      </div>
      {!items.length && <Empty art title={t("Rapor yok")}>{t("Bu kişi için henüz rapor girilmemiş.")}</Empty>}
      <ol className="relative space-y-3 border-l-2 border-dashed border-line pl-5">
        {items.map((r) => (
          <li key={r.id} className="relative">
            <span className={`absolute -left-[29px] top-6 h-3.5 w-3.5 rounded-full border-2 border-surface ${r.out_of_range ? "bg-bad" : "bg-brand"}`} />
            <div className={`card overflow-hidden ${r.deleted_at ? "opacity-60" : ""}`}>
              <div className="flex flex-wrap items-center gap-3 px-4 py-3">
                <input type="checkbox" className="h-4 w-4 accent-[rgb(var(--brand))]" checked={sel.includes(r.id)} onChange={() => toggle(r.id)}
                  disabled={!!r.deleted_at} aria-label={t("Karşılaştırma için seç")} />
                <button className="flex min-w-0 flex-1 flex-wrap items-center gap-x-4 gap-y-1 text-left" onClick={() => setOpen(open === r.id ? null : r.id)}>
                  <span className="text-lg font-extrabold">{fmtDate(r.report_date)}</span>
                  <span className="flex min-w-0 items-center gap-1.5 text-sm text-muted">
                    <Building2 size={15} className="shrink-0" />
                    <span className="truncate">{r.facility ?? (r.source === "manual" ? t("Elle giriş") : "—")}</span>
                  </span>
                  <span className="flex items-center gap-1 text-sm text-muted"><Layers size={15} /> {r.panel_count} {" "}{t("panel ·")}{" "}{r.result_count} {" "}{t("değer")}</span>
                  {r.out_of_range > 0 ? (
                    <span className="chip bg-badbg text-bad">{r.out_of_range} {" "}{t("referans dışı")}</span>
                  ) : (
                    <span className="chip bg-okbg text-ok">{t("Hepsi normal")}</span>
                  )}
                  {r.has_pdf && <FileText size={16} className="text-muted" aria-label={t("PDF var")} />}
                  <ChevronDown size={18} className={`ml-auto text-muted transition ${open === r.id ? "rotate-180" : ""}`} />
                </button>
              </div>
              {r.panel_names.length > 0 && open !== r.id && (
                <div className="truncate px-4 pb-3 pl-11 text-xs text-muted">{r.panel_names.join(" · ")}</div>
              )}
              {open === r.id && (
                <div className="border-t border-line bg-bg/40 p-4">
                  <ReportTable reportId={r.id} onChanged={reload} />
                </div>
              )}
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
}
