import { Building2, FileJson, FileText } from "lucide-react";
import { t } from "../lib/i18n";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Avatar } from "../components/Avatar";
import { Empty, ErrorBox, Modal, SelectPill, Spinner, StatusPill } from "../components/ui";
import { api, type Member, type ReportHeader } from "../lib/api";
import { useAuth } from "../lib/auth";
import { fmtDate, valueText, refText } from "../lib/format";
import { useApi } from "../lib/hooks";

function JsonImport({ open, onClose, members, onSaved }: { open: boolean; onClose: () => void; members: Member[]; onSaved: () => void }) {
  const [text, setText] = useState("");
  const [preview, setPreview] = useState<any>(null);
  const [err, setErr] = useState<any>(null);
  const [skip, setSkip] = useState(false);
  const parse = () => {
    try {
      return JSON.parse(text);
    } catch {
      throw { message: t("JSON okunamadı.") };
    }
  };
  const run = async (dry: boolean) => {
    setErr(null);
    try {
      const body = parse();
      const res = await api(`/api/app/reports?dry_run=${dry}&on_overlap=${skip ? "skip_existing" : "error"}`, { body });
      if (dry) setPreview(res);
      else {
        onSaved();
        onClose();
        setText("");
        setPreview(null);
      }
    } catch (e: any) {
      setErr(e);
      setPreview(null);
    }
  };
  return (
    <Modal open={open} onClose={onClose} wide title={t("JSON ile rapor ekle")}
      footer={<>
        <label className="mr-auto flex items-center gap-2 text-sm"><input type="checkbox" checked={skip} onChange={(e) => setSkip(e.target.checked)} /> {" "}{t("Var olan sonuçları atla")}</label>
        <button className="btn-ghost" onClick={() => run(true)} disabled={!text.trim()}>{t("Önizle")}</button>
        <button className="btn-primary" onClick={() => run(false)} disabled={!preview}>{t("Kaydet")}</button>
      </>}>
      <p className="mb-2 text-sm text-muted">
        {t("Ajanın ürettiği")}{" "}<code>POST /api/v1/reports</code> {" "}{t("gövdesini yapıştırın. Üye kimlikleri:")}{" "}{members.map((m) => `${m.display_name} = ${m.id}`).join(", ")}
      </p>
      <textarea className="input min-h-[200px] font-mono text-xs" value={text} onChange={(e) => { setText(e.target.value); setPreview(null); }} placeholder={t("{\"member_id\": \"mbr_…\", \"report_date\": \"2025-03-12\", \"panels\": [...]}")} />
      <div className="mt-3"><ErrorBox error={err} /></div>
      {err?.data?.conflicts?.length > 0 && <div className="mt-2 text-xs text-muted">{t("Çakışan:")}{" "}{err.data.conflicts.map((c: any) => c.raw_name).join(", ")}</div>}
      {preview && (
        <div className="mt-3 space-y-2">
          <div className="flex flex-wrap gap-2 text-sm">
            <span className="chip bg-surface2">{preview.summary.results_total} {" "}{t("değer")}</span>
            <span className="chip bg-badbg text-bad">{preview.summary.out_of_range} {" "}{t("referans dışı")}</span>
            <span className="chip bg-warnbg text-warn">{preview.summary.unmapped} {" "}{t("eşleşmemiş")}</span>
            <span className="chip bg-warnbg text-warn">{preview.summary.flag_mismatches} {" "}{t("işaret uyuşmazlığı")}</span>
          </div>
          <div className="max-h-[300px] overflow-y-auto rounded-xl border border-line">
            <table className="table-clean w-full">
              <tbody>
                {preview.results.map((r: any, i: number) => (
                  <tr key={i}><td>{r.display_name}{!r.test_key && <span className="ml-1 text-xs text-warn">{t("(eşleşmedi)")}</span>}</td><td className="font-semibold">{valueText(r)} {r.unit ?? ""}</td><td className="text-muted">{refText({ ...r, ref_low_exclusive: false, ref_high_exclusive: false })}</td><td><StatusPill flag={r.flag_computed} small /></td></tr>
                ))}
              </tbody>
            </table>
          </div>
          {preview.warnings.length > 0 && (
            <ul className="list-disc pl-5 text-xs text-muted">{preview.warnings.map((w: any, i: number) => <li key={i}>{w.raw_name ? <b>{w.raw_name}: </b> : null}{w.message}</li>)}</ul>
          )}
        </div>
      )}
    </Modal>
  );
}

export default function Reports() {
  const { me } = useAuth();
  const { data: mem } = useApi<{ items: Member[] }>("/api/app/members");
  const [all, setAll] = useState<(ReportHeader & { member: Member })[] | null>(null);
  const [who, setWho] = useState("all");
  const [onlyOut, setOnlyOut] = useState("all");
  const [imp, setImp] = useState(false);
  const [bump, setBump] = useState(0);

  useEffect(() => {
    if (!mem) return;
    Promise.all(mem.items.map((m) => api<{ items: ReportHeader[] }>(`/api/app/members/${m.id}/reports?limit=500`).then((r) => r.items.map((x) => ({ ...x, member: m })))))
      .then((lists) => setAll(lists.flat().sort((a, b) => b.report_date.localeCompare(a.report_date))));
  }, [mem, bump]);

  const items = useMemo(() => (all ?? []).filter((r) => (who === "all" || r.member_id === who) && (onlyOut === "all" || r.out_of_range > 0)), [all, who, onlyOut]);

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end gap-3">
        <div>
          <h1 className="text-[36px] font-extrabold tracking-tight">{t("Tahliller")}</h1>
          <p className="text-muted">{t("Ailenin tüm raporları, en yeniden eskiye")}</p>
        </div>
        <div className="ml-auto flex flex-wrap gap-2">
          <SelectPill value={who} onChange={setWho} options={[{ value: "all", label: t("Herkes") }, ...(mem?.items ?? []).map((m) => ({ value: m.id, label: m.display_name }))]} />
          <SelectPill value={onlyOut} onChange={setOnlyOut} options={[{ value: "all", label: t("Tüm raporlar") }, { value: "out", label: t("Referans dışı içerenler") }]} />
          {me?.role === "master" && <button className="btn-ghost" onClick={() => setImp(true)}><FileJson size={16} /> {" "}{t("JSON ile ekle")}</button>}
        </div>
      </div>
      {!all ? <Spinner /> : !items.length ? <Empty art title={t("Rapor bulunamadı")} /> : (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {items.map((r) => (
            <Link key={r.id} to={`/rapor/${r.id}`} className="card flex items-start gap-3 p-4 transition hover:-translate-y-0.5 hover:border-brand/40">
              <Avatar member={r.member} size={44} />
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className="font-extrabold">{fmtDate(r.report_date)}</span>
                  <span className="text-sm text-muted">· {r.member.display_name}</span>
                  {r.has_pdf && <FileText size={15} className="ml-auto text-muted" />}
                </div>
                <div className="flex items-center gap-1.5 truncate text-sm text-muted"><Building2 size={14} className="shrink-0" /> <span className="truncate">{r.facility ?? (r.source === "manual" ? t("Elle giriş") : "—")}</span></div>
                <div className="mt-1 truncate text-xs text-muted">{r.panel_names.join(" · ")}</div>
                <div className="mt-2 flex gap-2">
                  <span className="chip bg-surface2 text-muted">{r.result_count} {" "}{t("değer")}</span>
                  {r.out_of_range > 0 ? <span className="chip bg-badbg text-bad">{r.out_of_range} {" "}{t("referans dışı")}</span> : <span className="chip bg-okbg text-ok">{t("Hepsi normal")}</span>}
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
      <JsonImport open={imp} onClose={() => setImp(false)} members={mem?.items ?? []} onSaved={() => setBump((b) => b + 1)} />
    </div>
  );
}
