import { ArrowLeft, Building2 } from "lucide-react";
import { t } from "../lib/i18n";
import { Link, useParams } from "react-router-dom";
import { ReportTable } from "../components/ReportTable";
import { ErrorBox, Spinner } from "../components/ui";
import { fmtDate } from "../lib/format";
import { useApi } from "../lib/hooks";

export default function ReportPage() {
  const { reportId } = useParams();
  const { data, error, loading } = useApi<any>(`/api/app/reports/${reportId}`);
  const { data: member } = useApi<any>(data ? `/api/app/members/${data.member_id}` : null, [data?.member_id]);
  if (loading && !data) return <Spinner />;
  if (error) return <ErrorBox error={error} />;
  if (!data) return null;
  return (
    <div className="space-y-5">
      <Link to={`/uye/${data.member_id}?sekme=raporlar`} className="btn-ghost btn-sm"><ArrowLeft size={15} /> {member?.display_name ?? t("Geri")}</Link>
      <div className="card p-5 sm:p-7">
        <div className="mb-5 flex flex-wrap items-center gap-x-5 gap-y-2">
          <h1 className="text-[28px] font-extrabold">{fmtDate(data.report_date)}</h1>
          <span className="flex items-center gap-2 text-muted"><Building2 size={18} /> {data.facility ?? (data.source === "manual" ? t("Elle giriş") : "—")}</span>
          <span className="text-sm text-muted">{data.panel_count} {" "}{t("panel ·")}{" "}{data.result_count} {" "}{t("değer")}</span>
          {data.out_of_range > 0 && <span className="chip bg-badbg text-bad">{data.out_of_range} {" "}{t("referans dışı")}</span>}
        </div>
        <ReportTable reportId={data.id} />
      </div>
    </div>
  );
}
