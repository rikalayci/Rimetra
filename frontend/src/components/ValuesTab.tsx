import { LayoutGrid, List, Search } from "lucide-react";
import { t } from "../lib/i18n";
import { useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import type { Note, Summary, SummaryItem } from "../lib/api";
import { isOut, refText, valueText } from "../lib/format";
import { useApi } from "../lib/hooks";
import { CategoryIcon, categoryLabel } from "./icons";
import { Sparkline } from "./Sparkline";
import { QualStrip, TrendChart } from "./TrendChart";
import { ChangeBadge, Empty, MismatchBadge, SelectPill, Spinner, StatusPill } from "./ui";

type FilterKind = "all" | "out" | "mismatch";
type Period = "1y" | "all";

function ValueCard({ item, memberId }: { item: SummaryItem; memberId: string }) {
  const r = item.latest;
  const numeric = r.value_numeric !== null;
  return (
    <Link
      to={`/uye/${memberId}/test/${item.test_key}`}
      className={`card group flex w-full flex-col gap-1 p-4 transition hover:-translate-y-0.5 hover:border-brand/40 sm:w-[252px] ${
        isOut(r.flag_computed) ? "border-l-[3px] border-l-bad/60" : ""
      }`}
    >
      <div className="flex items-center gap-2">
        <CategoryIcon category={item.category} size={19} />
        <span className="truncate text-[15px] font-semibold">{item.display_name}</span>
      </div>
      <div className="mt-1 flex items-baseline gap-1.5">
        <span className={`font-extrabold tracking-tight ${numeric && !r.value_text ? "text-[30px]" : "text-xl"}`}>{valueText(r)}</span>
        <span className="text-[15px] text-muted">{r.unit ?? ""}</span>
        <span className="ml-auto"><ChangeBadge pct={item.change_pct} /></span>
      </div>
      <div className="text-[13px] text-muted">{t("Referans")}{" "}{refText(r)}</div>
      <div className="mt-1">
        {item.sparkline.length >= 2 ? (
          <Sparkline points={item.sparkline} flag={r.flag_computed} />
        ) : numeric && item.value_type === "numeric" ? (
          <div className="flex h-12 items-center text-xs text-muted">{t("Tek ölçüm")}</div>
        ) : (
          <div className="text-xs text-muted">{item.count > 1 ? t("{n} ölçüm", { n: item.count }) : t("Tek ölçüm")}</div>
        )}
      </div>
      <div className="mt-1 flex flex-wrap items-center gap-1.5">
        <StatusPill flag={r.flag_computed} soft />
        {r.flag_mismatch && <MismatchBadge />}
        {item.consecutive_out && (
          <span className="chip bg-badbg px-2 py-0.5 text-[11px] text-bad" title={t("Son iki ölçümde de referans dışı (görsel uyarı, tıbbi yorum değildir)")}>{t("2× üst üste")}</span>
        )}
      </div>
    </Link>
  );
}

function QualStripMini({ item }: { item: SummaryItem }) {
  return <QualStrip measurements={[item.latest]} compact />;
}

function FeaturedCard({ item, memberId }: { item: SummaryItem; memberId: string }) {
  const { data } = useApi<any>(`/api/app/members/${memberId}/tests/${item.test_key}/history`);
  const r = item.latest;
  const nav = useNavigate();
  return (
    <div className="card w-full cursor-pointer p-5 transition hover:border-brand/40 lg:w-[calc(252px*2+16px+252px)] xl:w-[772px]"
      onClick={() => nav(`/uye/${memberId}/test/${item.test_key}`)}>
      <div className="flex items-center gap-2">
        <CategoryIcon category={item.category} size={20} />
        <span className="text-lg font-semibold">{item.display_name}</span>
      </div>
      <div className="mt-2 flex flex-wrap items-center gap-3">
        <span className="text-[34px] font-extrabold leading-none tracking-tight">{valueText(r)}</span>
        <span className="text-lg text-muted">{r.unit ?? ""}</span>
        <StatusPill flag={r.flag_computed} />
        {r.flag_mismatch && <MismatchBadge />}
        <ChangeBadge pct={item.change_pct} />
      </div>
      <div className="mt-1 text-[15px] text-muted">{t("Normal aralık")}{" "}{refText(r)} {r.unit ?? ""}</div>
      <div className="mt-2">
        {data ? <TrendChart measurements={data.measurements} notes={data.notes as Note[]} height={240} /> : <div className="h-[240px]" />}
      </div>
    </div>
  );
}

function ListView({ items, memberId }: { items: SummaryItem[]; memberId: string }) {
  return (
    <div className="overflow-x-auto rounded-2xl border border-line">
      <table className="table-clean w-full min-w-[860px]">
        <thead className="bg-surface2">
          <tr><th>{t("Test")}</th><th>{t("Son değer")}</th><th>{t("Birim")}</th><th>{t("Referans")}</th><th className="w-40">{t("Trend")}</th><th>Δ</th><th>{t("Durum")}</th></tr>
        </thead>
        <tbody>
          {items.map((it) => (
            <tr key={it.test_key} className={isOut(it.latest.flag_computed) ? "bg-badbg/40" : ""}>
              <td><Link className="font-semibold hover:text-brand" to={`/uye/${memberId}/test/${it.test_key}`}>{it.display_name}</Link></td>
              <td className="font-bold">{valueText(it.latest)}</td>
              <td className="text-muted">{it.latest.unit ?? ""}</td>
              <td className="text-muted">{refText(it.latest)}</td>
              <td>{it.sparkline.length >= 2 ? <Sparkline points={it.sparkline} flag={it.latest.flag_computed} height={32} /> : <span className="text-xs text-muted">—</span>}</td>
              <td><ChangeBadge pct={it.change_pct} /></td>
              <td><div className="flex flex-wrap gap-1"><StatusPill flag={it.latest.flag_computed} small />{it.latest.flag_mismatch && <MismatchBadge />}</div></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function ValuesTab({ memberId, filter, period }: { memberId: string; filter: FilterKind; period: Period }) {
  const { data, loading } = useApi<Summary>(`/api/app/members/${memberId}/summary${period === "1y" ? "?since_days=365" : ""}`);
  const [q, setQ] = useState("");
  const [view, setView] = useState<"cards" | "list">(() => {
    try {
      return (localStorage.getItem("rimetra-values-view") as any) || "cards";
    } catch {
      return "cards";
    }
  });
  const setV = (v: "cards" | "list") => {
    setView(v);
    try {
      localStorage.setItem("rimetra-values-view", v);
    } catch {}
  };

  const items = useMemo(() => {
    let it = data?.items ?? [];
    if (filter === "out") it = it.filter((i) => isOut(i.latest.flag_computed));
    if (filter === "mismatch") it = it.filter((i) => i.latest.flag_mismatch);
    const s = q.trim().toLocaleLowerCase("tr-TR");
    if (s) it = it.filter((i) => i.display_name.toLocaleLowerCase("tr-TR").includes(s) || i.latest.raw_name.toLocaleLowerCase("tr-TR").includes(s));
    return it;
  }, [data, filter, q]);

  const featuredKey = useMemo(() => {
    const cands = items.filter((i) => i.sparkline.length >= 2);
    const out = cands.filter((i) => isOut(i.latest.flag_computed));
    const sev = (i: SummaryItem) => (i.latest.flag_computed === "high" || i.latest.flag_computed === "abnormal" ? 2 : i.latest.flag_computed === "low" ? 1 : 0);
    const pick = (out.length ? out : cands).sort((a, b) => sev(b) - sev(a) || b.count - a.count || (b.latest.sample_datetime ?? "").localeCompare(a.latest.sample_datetime ?? ""))[0];
    return pick?.test_key;
  }, [items]);

  const groups = useMemo(() => {
    const m = new Map<string, SummaryItem[]>();
    for (const i of items) {
      if (!m.has(i.category)) m.set(i.category, []);
      m.get(i.category)!.push(i);
    }
    return [...m.entries()];
  }, [items]);

  if (loading && !data) return <Spinner />;
  if (!data?.items.length && period === "1y")
    return <Empty title={t("Son 1 yılda sonuç yok")}>{t("Daha eski ölçümleri görmek için \"Tüm zamanlar\"ı seçin.")}</Empty>;
  if (!data?.items.length)
    return (
      <Empty art title={t("Henüz tahlil sonucu yok")}>
        {t("Ajan e-Nabız PDF'lerini API üzerinden girdiğinde değerler burada görünecek. Yönetim → Bağlantı bölümünden API anahtarı oluşturabilirsiniz.")}</Empty>
    );

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative w-full max-w-xs">
          <Search size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
          <input className="input pl-9" placeholder={t("Test ara…")} value={q} onChange={(e) => setQ(e.target.value)} />
        </div>
        <div className="text-sm text-muted">
          {items.length} {" "}{t("test ·")}{" "}{items.filter((i) => isOut(i.latest.flag_computed)).length} {" "}{t("referans dışı")}{data.unmapped_count > 0 && <> · <Link to="/eslesmemis" className="font-semibold text-warn underline-offset-2 hover:underline">{data.unmapped_count} {" "}{t("eşleşmemiş")}</Link></>}
        </div>
        <div className="ml-auto inline-flex rounded-xl border border-line bg-surface p-1">
          <button onClick={() => setV("cards")} className={`rounded-lg p-1.5 ${view === "cards" ? "bg-brandsoft text-brand" : "text-muted"}`} title={t("Kart görünümü")}><LayoutGrid size={16} /></button>
          <button onClick={() => setV("list")} className={`rounded-lg p-1.5 ${view === "list" ? "bg-brandsoft text-brand" : "text-muted"}`} title={t("Liste görünümü")}><List size={16} /></button>
        </div>
      </div>
      {!items.length && <Empty title={t("Filtreye uyan test yok")} />}
      {view === "list" ? (
        <div className="space-y-6">
          {groups.map(([cat, its]) => (
            <section key={cat}>
              <h3 className="h-section mb-3"><CategoryIcon category={cat} size={22} /> {categoryLabel(cat)}</h3>
              <ListView items={its} memberId={memberId} />
            </section>
          ))}
        </div>
      ) : (
        <div className="flex flex-wrap gap-x-6 gap-y-7">
          {groups.map(([cat, its]) => {
            const featured = its.find((i) => i.test_key === featuredKey);
            const rest = its.filter((i) => i !== featured);
            return (
              <section key={cat} className={`flex w-full flex-col sm:w-auto ${featured ? "max-w-full" : "sm:max-w-[792px]"}`}>
                <h3 className="h-section mb-3"><CategoryIcon category={cat} size={22} /> {categoryLabel(cat)}</h3>
                <div className="flex flex-wrap gap-4">
                  {featured && <FeaturedCard item={featured} memberId={memberId} />}
                  {rest.map((i) => <ValueCard key={i.test_key} item={i} memberId={memberId} />)}
                </div>
              </section>
            );
          })}
        </div>
      )}
    </div>
  );
}

export const FILTER_OPTIONS = [
  { value: "all" as FilterKind, get label() { return t("Tüm sonuçlar"); } },
  { value: "out" as FilterKind, get label() { return t("Sadece referans dışı"); } },
  { value: "mismatch" as FilterKind, get label() { return t("İşaret uyuşmazlığı"); } },
];
export const PERIOD_OPTIONS = [
  { value: "1y" as Period, get label() { return t("Son 1 yıl"); } },
  { value: "all" as Period, get label() { return t("Tüm zamanlar"); } },
];
export type { FilterKind, Period };
export { SelectPill };
