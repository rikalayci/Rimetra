import { AlertCircle, CalendarDays, CheckCircle2, ChevronRight, Download, Plus, UserPlus } from "lucide-react";
import { t } from "../lib/i18n";
import { useEffect, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { Avatar } from "../components/Avatar";
import { EmptyArt, HomeIllustration } from "../components/icons";
import { ExportModal, ManualEntryModal } from "../components/MemberActions";
import { NotesTab } from "../components/NotesTab";
import { ReportsTab } from "../components/ReportsTab";
import { Segmented, SelectPill, Spinner } from "../components/ui";
import { FILTER_OPTIONS, PERIOD_OPTIONS, ValuesTab, type FilterKind, type Period } from "../components/ValuesTab";
import type { DashboardMember } from "../lib/api";
import { useAuth } from "../lib/auth";
import { fmtDate, possessive } from "../lib/format";
import { useApi } from "../lib/hooks";

function MemberCard({ m, selected, onClick }: { m: DashboardMember; selected: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className={`card group flex w-[300px] shrink-0 flex-col p-4 text-left transition sm:w-auto ${
        selected ? "border-2 border-brand/70 bg-brandsoft/60 dark:bg-brandsoft" : "hover:border-brand/40"
      }`}
    >
      <div className="flex items-center gap-4">
        <Avatar member={m} size={104} />
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="truncate text-[22px] font-bold">{m.display_name}</span>
            <ChevronRight size={20} className="ml-auto shrink-0 text-muted transition group-hover:translate-x-0.5" />
          </div>
          <div className="mt-1 flex items-start gap-2 text-sm text-muted">
            <CalendarDays size={18} className="mt-0.5 shrink-0" />
            <div>
              <div>{t("Son tahlil")}</div>
              <div className="text-[15px] font-bold text-ink">{m.last_report_date ? fmtDate(m.last_report_date) : "—"}</div>
            </div>
          </div>
          <div className="mt-2">
            {!m.last_report_date ? (
              <span className="chip bg-surface2 text-muted">{t("Henüz tahlil yok")}</span>
            ) : m.last_report_out_of_range > 0 ? (
              <span className="chip bg-badbg px-3 py-1.5 text-[13px] text-bad">
                <AlertCircle size={16} className="fill-bad text-badbg" /> {m.last_report_out_of_range} {" "}{t("değere dikkat")}</span>
            ) : (
              <span className="chip bg-okbg px-3 py-1.5 text-[13px] text-ok">
                <CheckCircle2 size={16} className="fill-ok text-okbg" /> {" "}{t("Her şey yolunda")}</span>
            )}
          </div>
        </div>
      </div>
      {m.recent_reports.length > 0 && (
        <div className="mt-3 space-y-0.5 border-t border-line/80 pt-2">
          {m.recent_reports.map((r) => (
            <div key={r.id} className="flex items-center gap-2 text-xs text-muted">
              <span className="w-[72px] font-semibold text-ink/80">{fmtDate(r.report_date)}</span>
              <span className="truncate">{r.facility ?? (r.source === "manual" ? t("Elle giriş") : "—")}</span>
              {r.out_of_range > 0 && <span className="ml-auto shrink-0 font-semibold text-bad">{r.out_of_range}</span>}
            </div>
          ))}
        </div>
      )}
      {m.reminders_due > 0 && <div className="mt-2 text-xs font-semibold text-warn">⏰ {m.reminders_due} {" "}{t("kontrolün zamanı geldi")}</div>}
    </button>
  );
}

type Tab = "degerler" | "raporlar" | "notlar";

export default function Family() {
  const { me } = useAuth();
  const { memberId } = useParams();
  const [sp, setSp] = useSearchParams();
  const nav = useNavigate();
  const { data, loading, reload } = useApi<{ members: DashboardMember[] }>("/api/app/dashboard");
  const tab = (sp.get("sekme") as Tab) || "degerler";
  const [filter, setFilter] = useState<FilterKind>("all");
  const [period, setPeriod] = useState<Period>("all");
  const [manual, setManual] = useState(false);
  const [exp, setExp] = useState(false);
  const [bump, setBump] = useState(0);

  const members = data?.members ?? [];
  const selectedId = memberId ?? me?.member_id ?? members[0]?.id;
  const selected = members.find((m) => m.id === selectedId) ?? members[0];

  useEffect(() => {
    if (!memberId && selected && members.length) nav(`/uye/${selected.id}${sp.toString() ? "?" + sp.toString() : ""}`, { replace: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [memberId, selected?.id]);

  const setTab = (tx: Tab) => {
    const n = new URLSearchParams(sp);
    n.set("sekme", tx);
    setSp(n, { replace: true });
  };
  const master = me?.role === "master";

  return (
    <div className="space-y-6">
      <div className="relative flex min-h-[112px] items-end justify-between gap-4 pb-2">
        <div>
          <h1 className="text-[40px] font-extrabold leading-tight tracking-tight">{t("Ailem")}</h1>
          <p className="text-[17px] text-muted">{t("Herkesin sağlık kayıtları, bir arada")}</p>
        </div>
        <div className="pointer-events-none absolute -top-9 right-0 hidden h-[150px] w-[700px] lg:block">
          <div className="absolute left-0 top-0 h-full w-[480px]"><HomeIllustration /></div>
          <div className="absolute right-2 top-4 rotate-[-6deg] text-right font-hand text-[26px] leading-[1.05] text-[#B9826A]">
            {t("Daha sağlıklı")}<br />{t("daha mutlu yarınlara")}<br />{t("birlikte ♡")}</div>
        </div>
      </div>

      {loading && !data ? (
        <Spinner />
      ) : !members.length ? (
        <div className="card flex flex-col items-center gap-3 p-10 text-center">
          <EmptyArt size={200} />
          <div className="text-lg font-bold">{t("Henüz aile üyesi yok")}</div>
          {master && <Link to="/yonetim?sekme=uyeler" className="btn-primary"><Plus size={16} /> {" "}{t("Üye ekle")}</Link>}
        </div>
      ) : (
        <>
          <div className="-mx-4 flex gap-4 overflow-x-auto px-4 pb-2 sm:mx-0 sm:grid sm:grid-cols-2 sm:overflow-visible sm:px-0 xl:grid-cols-4">
            {members.map((m) => (
              <MemberCard key={m.id} m={m} selected={m.id === selected?.id} onClick={() => nav(`/uye/${m.id}?sekme=${tab}`)} />
            ))}
            {master && members.length < 4 && (
              <Link to="/yonetim?sekme=uyeler" className="flex min-h-[140px] w-[200px] shrink-0 flex-col items-center justify-center gap-2 rounded-card border-2 border-dashed border-line text-muted hover:border-brand/50 hover:text-brand sm:w-auto">
                <UserPlus size={28} /> <span className="font-semibold">{t("Üye ekle")}</span>
              </Link>
            )}
          </div>

          {selected && (
            <section className="card space-y-6 p-4 sm:p-6">
              <div className="flex flex-wrap items-center gap-x-6 gap-y-3">
                <h2 className="text-[28px] font-extrabold tracking-tight">{possessive(selected.display_name)} {" "}{t("tahlilleri")}</h2>
                <Segmented<Tab>
                  value={tab}
                  onChange={setTab}
                  options={[
                    { value: "degerler", label: t("Değerler") },
                    { value: "raporlar", label: t("Raporlar") },
                    { value: "notlar", label: t("Notlar") },
                  ]}
                />
                <div className="ml-auto flex flex-wrap items-center gap-2">
                  {tab === "degerler" && (
                    <>
                      <SelectPill value={filter} onChange={setFilter} options={FILTER_OPTIONS} />
                      <SelectPill value={period} onChange={setPeriod} options={PERIOD_OPTIONS} />
                    </>
                  )}
                  <button className="btn-ghost" onClick={() => setExp(true)} title={t("Doktor için dışa aktar")}><Download size={16} /> <span className="hidden sm:inline">{t("Dışa aktar")}</span></button>
                  {master && <button className="btn-ghost" onClick={() => setManual(true)}><Plus size={16} /> <span className="hidden sm:inline">{t("Değer gir")}</span></button>}
                </div>
              </div>
              <div key={selected.id + bump}>
                {tab === "degerler" && <ValuesTab memberId={selected.id} filter={filter} period={period} />}
                {tab === "raporlar" && <ReportsTab memberId={selected.id} />}
                {tab === "notlar" && <NotesTab memberId={selected.id} />}
              </div>
              <ManualEntryModal memberId={selected.id} open={manual} onClose={() => setManual(false)} onSaved={() => { setBump((b) => b + 1); reload(); }} />
              <ExportModal memberId={selected.id} open={exp} onClose={() => setExp(false)} />
            </section>
          )}
        </>
      )}
    </div>
  );
}
