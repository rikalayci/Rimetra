import { FileText, RotateCcw, Trash2 } from "lucide-react";
import { t } from "../lib/i18n";
import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import { fmtDate, fmtDateTime, isOut, refText, SPECIMEN_LABEL, valueText } from "../lib/format";
import { useApi } from "../lib/hooks";
import { ErrorBox, MismatchBadge, Spinner, StatusPill } from "./ui";

export function ReportTable({ reportId, onChanged }: { reportId: string; onChanged?: () => void }) {
  const { me } = useAuth();
  const { data, error, loading, reload } = useApi<any>(`/api/app/reports/${reportId}`);
  const [err, setErr] = useState<any>(null);
  const [uploading, setUploading] = useState(false);
  if (loading && !data) return <Spinner />;
  if (error) return <ErrorBox error={error} />;
  if (!data) return null;
  const master = me?.role === "master";

  const del = async () => {
    if (!confirm(t("Bu rapor ve sonuçları silinsin mi? (30 gün içinde geri alınabilir)"))) return;
    try {
      await api(`/api/app/reports/${reportId}`, { method: "DELETE" });
      onChanged?.();
      reload();
    } catch (e) {
      setErr(e);
    }
  };
  const restore = async () => {
    try {
      await api(`/api/app/reports/${reportId}/restore`, { method: "POST" });
      onChanged?.();
      reload();
    } catch (e) {
      setErr(e);
    }
  };
  const upload = async (f: File) => {
    const fd = new FormData();
    fd.append("file", f);
    setUploading(true);
    try {
      await api(`/api/app/reports/${reportId}/pdf`, { form: fd });
      reload();
      onChanged?.();
    } catch (e) {
      setErr(e);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        {data.has_pdf ? (
          <a className="btn-primary btn-sm" href={`/api/app/reports/${reportId}/pdf`} target="_blank" rel="noreferrer">
            <FileText size={15} /> {" "}{t("Orijinal PDF'i aç")}</a>
        ) : master && !data.deleted_at ? (
          <label className="btn-ghost btn-sm cursor-pointer">
            <FileText size={15} /> {uploading ? t("Yükleniyor…") : t("PDF ekle")}
            <input type="file" accept="application/pdf" className="hidden" onChange={(e) => e.target.files?.[0] && upload(e.target.files[0])} />
          </label>
        ) : (
          <span className="text-xs text-muted">{t("Orijinal PDF eklenmemiş")}</span>
        )}
        <Link to={`/rapor/${reportId}`} className="btn-ghost btn-sm">{t("Tam sayfa")}</Link>
        {master && !data.deleted_at && (
          <button className="btn-ghost btn-sm text-bad" onClick={del}><Trash2 size={15} /> {" "}{t("Sil")}</button>
        )}
        {master && data.deleted_at && (
          <button className="btn-ghost btn-sm" onClick={restore}><RotateCcw size={15} /> {" "}{t("Geri al")}</button>
        )}
        {data.deleted_at && <span className="chip bg-badbg text-bad">{t("Silindi ·")}{" "}{fmtDate(data.deleted_at)}</span>}
      </div>
      <ErrorBox error={err} />
      {data.panels.map((p: any) => (
        <div key={p.id} className="overflow-hidden rounded-2xl border border-line">
          <div className="flex flex-wrap items-center justify-between gap-2 bg-surface2 px-4 py-2.5">
            <div className="font-bold">{p.name}</div>
            <div className="text-xs text-muted">
              {p.specimen ? SPECIMEN_LABEL[p.specimen] + " · " : ""}{t("Numune:")}{" "}{fmtDateTime(p.sample_datetime)}
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="table-clean w-full min-w-[640px]">
              <thead>
                <tr><th>{t("Test")}</th><th>{t("Sonuç")}</th><th>{t("Birim")}</th><th>{t("Referans")}</th><th>{t("Durum")}</th></tr>
              </thead>
              <tbody>
                {p.results.map((r: any) => {
                  const out = isOut(r.flag_computed);
                  return (
                    <tr key={r.id} className={out ? "bg-badbg/60" : ""}>
                      <td>
                        {r.test_key ? (
                          <Link to={`/uye/${data.member_id}/test/${r.test_key}`} className="font-semibold hover:text-brand">{r.display_name}</Link>
                        ) : (
                          <span className="font-semibold">{r.raw_name} <span className="chip ml-1 bg-surface2 px-2 py-0 text-[10px] text-muted">{t("eşleşmemiş")}</span></span>
                        )}
                        {r.test_key && r.raw_name !== r.display_name && <div className="text-[11px] text-muted">{r.raw_name}</div>}
                      </td>
                      <td className={`font-bold ${out ? "text-bad" : ""}`}>{valueText(r)}</td>
                      <td className="text-muted">{r.unit ?? ""}</td>
                      <td className="text-muted">
                        {refText(r)}
                        {r.ref_note && <div className="max-w-[260px] text-[11px] leading-snug opacity-80" title={r.ref_note}>{r.ref_note}</div>}
                      </td>
                      <td>
                        <div className="flex flex-wrap items-center gap-1">
                          <StatusPill flag={r.flag_computed} small />
                          {r.flag_mismatch && <MismatchBadge />}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      ))}
    </div>
  );
}
