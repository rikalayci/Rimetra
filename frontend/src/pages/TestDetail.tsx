import { ArrowLeft, Download, StickyNote } from "lucide-react";
import { t } from "../lib/i18n";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { CategoryIcon } from "../components/icons";
import { ExportModal } from "../components/MemberActions";
import { TestInfoCard } from "../components/TestInfo";
import { QualStrip, TrendChart } from "../components/TrendChart";
import { ErrorBox, MismatchBadge, Spinner, StatusPill } from "../components/ui";
import type { Member, Note, ResultRow, TestDef } from "../lib/api";
import { catLabel, fmtDate, fmtDateTime, isOut, refText, SPECIMEN_LABEL, valueText } from "../lib/format";
import { useApi } from "../lib/hooks";

export default function TestDetail() {
  const { memberId, testKey } = useParams();
  const { data, error, loading } = useApi<{ test: TestDef; measurements: ResultRow[]; notes: Note[] }>(
    `/api/app/members/${memberId}/tests/${testKey}/history`,
  );
  const { data: member } = useApi<Member>(`/api/app/members/${memberId}`);
  const [exp, setExp] = useState(false);
  if (loading && !data) return <Spinner />;
  if (error) return <ErrorBox error={error} />;
  if (!data) return null;
  const ms = data.measurements;
  const last = ms[ms.length - 1];
  const numericCount = ms.filter((m) => m.value_numeric !== null).length;
  const qualitative = numericCount === 0;
  const refChanged = new Set(ms.map((m) => refText(m))).size > 1;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-3">
        <Link to={`/uye/${memberId}`} className="btn-ghost btn-sm"><ArrowLeft size={15} /> {member?.display_name ?? t("Geri")}</Link>
        <button className="btn-ghost btn-sm ml-auto" onClick={() => setExp(true)}><Download size={15} /> {" "}{t("Dışa aktar")}</button>
      </div>
      <div className="card p-5 sm:p-7">
        <div className="flex flex-wrap items-center gap-3">
          <CategoryIcon category={data.test.category} size={26} />
          <h1 className="text-[28px] font-extrabold tracking-tight">{data.test.display_name}</h1>
          <span className="chip bg-surface2 text-muted">{catLabel(data.test.category)} · {SPECIMEN_LABEL[data.test.specimen] ?? data.test.specimen}</span>
        </div>
        {last && (
          <div className="mt-3 flex flex-wrap items-center gap-3">
            <span className="text-[38px] font-extrabold leading-none tracking-tight">{valueText(last)}</span>
            <span className="text-lg text-muted">{last.unit ?? ""}</span>
            <StatusPill flag={last.flag_computed} />
            {last.flag_mismatch && <MismatchBadge />}
            <span className="text-sm text-muted">· {fmtDate(last.sample_datetime)} {" "}{t("· Referans")}{" "}{refText(last)} {last.unit ?? ""}</span>
          </div>
        )}
        {refChanged && <div className="mt-2 text-xs text-muted">{t("Referans aralığı ölçümler arasında değişmiş; gölgeli bant her ölçümün kendi aralığını gösterir.")}</div>}
        <div className="mt-5">
          {qualitative ? (
            <QualStrip measurements={ms} />
          ) : (
            <TrendChart measurements={ms} notes={data.notes} height={380} />
          )}
        </div>
        {data.notes.length > 0 && (
          <div className="mt-4 flex flex-wrap gap-2">
            {data.notes.map((n) => (
              <span key={n.id} className="chip bg-surface2 text-muted"><StickyNote size={13} /> {fmtDate(n.date)} · {n.text}</span>
            ))}
          </div>
        )}
      </div>

      <TestInfoCard test={data.test} flag={last?.flag_computed} />

      <div className="card overflow-hidden">
        <div className="border-b border-line px-5 py-3 font-bold">{t("Tüm ölçümler (")}{ms.length})</div>
        <div className="overflow-x-auto">
          <table className="table-clean w-full min-w-[760px]">
            <thead><tr><th>{t("Numune zamanı")}</th><th>{t("Değer")}</th><th>{t("Referans")}</th><th>{t("Durum")}</th><th>{t("Kurum")}</th><th>{t("Belgedeki ad")}</th></tr></thead>
            <tbody>
              {[...ms].reverse().map((m) => (
                <tr key={m.id} className={isOut(m.flag_computed) ? "bg-badbg/50" : ""}>
                  <td className="whitespace-nowrap">{fmtDateTime(m.sample_datetime)}</td>
                  <td className="font-bold">{valueText(m)} <span className="font-normal text-muted">{m.unit ?? ""}</span></td>
                  <td className="text-muted">{refText(m)}{m.ref_note && <div className="text-[11px]">{m.ref_note}</div>}</td>
                  <td><div className="flex flex-wrap gap-1"><StatusPill flag={m.flag_computed} small />{m.flag_mismatch && <MismatchBadge />}</div></td>
                  <td className="max-w-[260px] truncate text-muted"><Link to={`/rapor/${m.report_id}`} className="hover:text-brand">{m.facility ?? (m.source === "manual" ? t("Elle giriş") : "—")}</Link></td>
                  <td className="text-xs text-muted">{m.raw_name}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      <p className="text-xs text-muted">{t("Rimetra yalnızca değeri, referansı ve trendi gösterir; tıbbi yorum veya teşhis içermez.")}</p>
      {memberId && <ExportModal memberId={memberId} open={exp} onClose={() => setExp(false)} preselect={testKey ? [testKey] : []} />}
    </div>
  );
}
