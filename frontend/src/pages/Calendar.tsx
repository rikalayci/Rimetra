import { Bell, ChevronLeft, ChevronRight, FileText, StickyNote } from "lucide-react";
import { t } from "../lib/i18n";
import { useState } from "react";
import { Link } from "react-router-dom";
import { Spinner } from "../components/ui";
import { fmtDate } from "../lib/format";
import { useApi } from "../lib/hooks";

const MONTHS = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"];
const DAYS = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"];

export default function Calendar() {
  const now = new Date();
  const [ym, setYm] = useState({ y: now.getFullYear(), m: now.getMonth() + 1 });
  const { data, loading } = useApi<any>(`/api/app/calendar?year=${ym.y}&month=${ym.m}`);
  const shift = (d: number) => setYm(({ y, m }) => {
    const n = m + d;
    return n < 1 ? { y: y - 1, m: 12 } : n > 12 ? { y: y + 1, m: 1 } : { y, m: n };
  });
  const first = new Date(ym.y, ym.m - 1, 1);
  const offset = (first.getDay() + 6) % 7;
  const daysIn = new Date(ym.y, ym.m, 0).getDate();
  const cells = Array.from({ length: Math.ceil((offset + daysIn) / 7) * 7 }, (_, i) => i - offset + 1);
  const byDay: Record<number, any[]> = {};
  for (const e of data?.events ?? []) {
    const d = +e.date.slice(8, 10);
    (byDay[d] ||= []).push(e);
  }
  const today = now.getFullYear() === ym.y && now.getMonth() + 1 === ym.m ? now.getDate() : -1;
  const upcoming = (data?.reminders ?? []).filter((r: any) => r.status !== "ok");

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end gap-3">
        <div>
          <h1 className="text-[36px] font-extrabold tracking-tight">{t("Takvim")}</h1>
          <p className="text-muted">{t("Tahliller, notlar ve kontrol hatırlatıcıları")}</p>
        </div>
        <div className="ml-auto flex items-center gap-2">
          <button className="btn-ghost btn-sm" onClick={() => shift(-1)} aria-label={t("Önceki ay")}><ChevronLeft size={16} /></button>
          <div className="w-40 text-center text-lg font-bold">{t(MONTHS[ym.m - 1])} {ym.y}</div>
          <button className="btn-ghost btn-sm" onClick={() => shift(1)} aria-label={t("Sonraki ay")}><ChevronRight size={16} /></button>
          <button className="btn-ghost btn-sm" onClick={() => setYm({ y: now.getFullYear(), m: now.getMonth() + 1 })}>{t("Bugün")}</button>
        </div>
      </div>
      <div className="grid gap-5 xl:grid-cols-[1fr_340px]">
        <div className="card overflow-hidden">
          {loading && !data ? <Spinner /> : (
            <div className="grid grid-cols-7">
              {DAYS.map((d) => <div key={d} className="border-b border-line bg-surface2 py-2 text-center text-xs font-bold text-muted">{t(d)}</div>)}
              {cells.map((d, i) => (
                <div key={i} className={`min-h-[96px] border-b border-r border-line p-1.5 ${d < 1 || d > daysIn ? "bg-bg/60" : ""}`}>
                  {d >= 1 && d <= daysIn && (
                    <>
                      <div className={`mb-1 inline-flex h-6 w-6 items-center justify-center rounded-full text-xs font-bold ${d === today ? "bg-brand text-white" : "text-muted"}`}>{d}</div>
                      <div className="space-y-1">
                        {(byDay[d] ?? []).map((e) => {
                          const to = e.type === "report" ? `/rapor/${e.id}` : e.type === "note" ? `/uye/${e.member_id}?sekme=notlar` : `/uye/${e.member_id}?sekme=notlar`;
                          const cls = e.type === "report" ? (e.out_of_range ? "bg-badbg text-bad" : "bg-okbg text-ok") : e.type === "note" ? "bg-warnbg text-warn" : "bg-brandsoft text-brand";
                          const Icon = e.type === "report" ? FileText : e.type === "note" ? StickyNote : Bell;
                          return (
                            <Link key={e.type + e.id} to={to} className={`flex items-center gap-1 truncate rounded-md px-1.5 py-0.5 text-[11px] font-semibold ${cls}`} title={`${e.member_name}: ${e.title}`}>
                              <Icon size={11} className="shrink-0" /> <span className="truncate">{e.member_name} · {e.title}</span>
                            </Link>
                          );
                        })}
                      </div>
                    </>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
        <div className="card h-fit space-y-3 p-4">
          <div className="flex items-center gap-2 font-bold"><Bell size={17} /> {" "}{t("Yaklaşan kontroller")}</div>
          {!upcoming.length && <div className="text-sm text-muted">{t("Zamanı gelen kontrol yok. Hatırlatıcıları üye sayfasındaki \"Notlar\" sekmesinden ekleyebilirsiniz.")}</div>}
          {upcoming.map((r: any) => (
            <Link key={r.id} to={`/uye/${r.member_id}/test/${r.test_key}`} className="flex items-center gap-2 rounded-xl px-2 py-1.5 text-sm hover:bg-surface2">
              <div className="flex-1">
                <div className="font-semibold">{r.member_name} · {r.display_name}</div>
                <div className="text-xs text-muted">{r.last_done ? t("Son: {date}", { date: fmtDate(r.last_done) }) : t("Hiç yapılmadı")} · {fmtDate(r.due_date)}</div>
              </div>
              <span className={`chip ${r.status === "soon" ? "bg-warnbg text-warn" : "bg-badbg text-bad"}`}>{r.status === "soon" ? t("Yaklaşıyor") : t("Zamanı geldi")}</span>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
