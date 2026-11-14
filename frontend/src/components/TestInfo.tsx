import { ArrowDownCircle, ArrowUpCircle, ChevronDown, Info } from "lucide-react";
import { t } from "../lib/i18n";
import { useState, type ReactNode } from "react";
import type { TestDef } from "../lib/api";

type Flag = string | null | undefined;

/** Düşük/yüksek kutularının başlıkları; nitel testlerde "pozitif" dili kullanılır. */
export function infoLabels(tx: Pick<TestDef, "value_type" | "info_low">) {
  const qualitativeOnly = tx.value_type !== "numeric" && !tx.info_low;
  return {
    low: t("Düşük çıkarsa"),
    high: qualitativeOnly ? t("Pozitif / anormal çıkarsa") : t("Yüksek çıkarsa"),
  };
}

export const hasInfo = (tx: Partial<TestDef>) => !!(tx.info_what || tx.info_low || tx.info_high);

/** Test detay sayfasındaki "Bu test ne anlatır?" kartı. Son sonucun durumuna uyan kutu vurgulanır. */
export function TestInfoCard({ test, flag }: { test: TestDef; flag?: Flag }) {
  const [open, setOpen] = useState(true);
  if (!hasInfo(test)) return null;
  const labels = infoLabels(test);
  const lowActive = flag === "low";
  const highActive = flag === "high" || flag === "abnormal";
  return (
    <div className="card overflow-hidden">
      <button
        type="button"
        className="flex w-full items-center gap-2 px-5 py-3 text-left font-bold"
        onClick={() => setOpen(!open)}
        aria-expanded={open}
      >
        <Info size={17} className="text-brand" /> {" "}{t("Bu test ne anlatır?")}<ChevronDown size={17} className={`ml-auto text-muted transition-transform ${open ? "rotate-180" : ""}`} />
      </button>
      {open && (
        <div className="space-y-4 border-t border-line px-5 pb-5 pt-4">
          {test.info_what && <p className="leading-relaxed">{test.info_what}</p>}
          {(test.info_low || test.info_high) && (
            <div className={`grid gap-3 ${test.info_low && test.info_high ? "sm:grid-cols-2" : ""}`}>
              {test.info_low && (
                <InfoBox icon={<ArrowDownCircle size={16} />} title={labels.low} text={test.info_low} active={lowActive} />
              )}
              {test.info_high && (
                <InfoBox icon={<ArrowUpCircle size={16} />} title={labels.high} text={test.info_high} active={highActive} />
              )}
            </div>
          )}
          <p className="text-xs text-muted">
            {t("Bu açıklamalar genel bilgilendirme içindir, teşhis yerine geçmez. Tek bir değer tek başına çok şey söylemez; sonuçlarınızı doktorunuzla birlikte değerlendirin.")}</p>
        </div>
      )}
    </div>
  );
}

function InfoBox({ icon, title, text, active }: { icon: ReactNode; title: string; text: string; active: boolean }) {
  return (
    <div className={`rounded-xl border p-4 ${active ? "border-warn bg-warnbg/60" : "border-line bg-surface2"}`}>
      <div className={`mb-1.5 flex items-center gap-1.5 text-sm font-bold ${active ? "text-warn" : ""}`}>
        {icon} {title}
        {active && <span className="ml-auto text-[11px] font-semibold">{t("Son sonucunuz bu yönde")}</span>}
      </div>
      <p className="text-sm leading-relaxed text-muted">{text}</p>
    </div>
  );
}
