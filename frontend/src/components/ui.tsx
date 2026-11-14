import { createPortal } from "react-dom";
import { locale, t } from "../lib/i18n";
import { AlertCircle, AlertTriangle, CheckCircle2, ChevronDown, HelpCircle, Loader2, X } from "lucide-react";
import { useEffect, type ReactNode } from "react";
import type { Flag } from "../lib/api";
import { EmptyArt } from "./icons";
import { FLAG_LABEL } from "../lib/format";

export function StatusPill({ flag, small, soft }: { flag: Flag; small?: boolean; soft?: boolean }) {
  const cls = small ? "px-2 py-0.5 text-[11px]" : "px-3 py-1 text-xs";
  if (flag === "normal")
    return (
      <span className={`chip bg-okbg text-ok ${cls}`}>
        <CheckCircle2 size={small ? 12 : 14} className="fill-ok text-okbg" /> {" "}{t("Normal")}</span>
    );
  if (flag === "low")
    return (
      <span className={`chip bg-warnbg text-warn ${cls}`}>
        <AlertCircle size={small ? 12 : 14} className="fill-warn text-warnbg" /> {soft ? t("Biraz düşük") : FLAG_LABEL.low}
      </span>
    );
  if (flag === "high" || flag === "abnormal")
    return (
      <span className={`chip bg-badbg text-bad ${cls}`}>
        <AlertCircle size={small ? 12 : 14} className="fill-bad text-badbg" /> {FLAG_LABEL[flag]}
      </span>
    );
  return (
    <span className={`chip bg-surface2 text-muted ${cls}`}>
      <HelpCircle size={small ? 12 : 14} /> {" "}{t("Referans yok")}</span>
  );
}

export function MismatchBadge() {
  return (
    <span
      className="chip bg-warnbg px-2 py-0.5 text-[11px] text-warn"
      title={t("Belgedeki işaret (yeşil tik / kırmızı ünlem) ile Rimetra'nın hesapladığı durum uyuşmuyor.")}
    >
      <AlertTriangle size={12} /> {" "}{t("İşaret uyuşmuyor")}</span>
  );
}

export function Spinner({ label }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-2 py-10 text-muted">
      <Loader2 className="animate-spin" size={18} /> {label ?? t("Yükleniyor…")}
    </div>
  );
}

export function Empty({ title, children, icon, art }: { title: string; children?: ReactNode; icon?: ReactNode; art?: boolean }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 rounded-card border border-dashed border-line px-6 py-10 text-center">
      {art ? <EmptyArt size={180} /> : icon}
      <div className="font-semibold">{title}</div>
      {children && <div className="max-w-md text-sm text-muted">{children}</div>}
    </div>
  );
}

export function ErrorBox({ error }: { error: { message: string } | null | undefined }) {
  if (!error) return null;
  return (
    <div className="flex items-start gap-2 rounded-xl border border-bad/30 bg-badbg px-3 py-2 text-sm text-bad">
      <AlertCircle size={16} className="mt-0.5 shrink-0" /> <span>{error.message}</span>
    </div>
  );
}

export function Modal({
  open, onClose, title, children, wide, footer,
}: { open: boolean; onClose: () => void; title: ReactNode; children: ReactNode; wide?: boolean; footer?: ReactNode }) {
  useEffect(() => {
    if (!open) return;
    const k = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", k);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", k);
      document.body.style.overflow = prev;
    };
  }, [open, onClose]);
  if (!open) return null;
  // body'ye portal: üst menü gibi backdrop-blur'lu kapsayıcıların içinde "fixed" konum bozulmasın
  return createPortal(
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/30 p-0 backdrop-blur-[2px] sm:items-center sm:p-6" onMouseDown={onClose}>
      <div
        className={`card flex max-h-[92vh] w-full flex-col overflow-hidden rounded-b-none sm:rounded-b-card ${wide ? "max-w-5xl" : "max-w-lg"}`}
        onMouseDown={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
      >
        <div className="flex items-center justify-between gap-3 border-b border-line px-5 py-4">
          <div className="text-lg font-bold">{title}</div>
          <button className="rounded-full p-1.5 text-muted hover:bg-surface2" onClick={onClose} aria-label={t("Kapat")}>
            <X size={18} />
          </button>
        </div>
        <div className="overflow-y-auto px-5 py-4">{children}</div>
        {footer && <div className="flex flex-wrap justify-end gap-2 border-t border-line px-5 py-3">{footer}</div>}
      </div>
    </div>,
    document.body,
  );
}

export function Segmented<T extends string>({
  value, onChange, options,
}: { value: T; onChange: (v: T) => void; options: { value: T; label: ReactNode }[] }) {
  return (
    <div className="inline-flex rounded-full border border-line bg-surface2 p-1">
      {options.map((o) => (
        <button
          key={o.value}
          onClick={() => onChange(o.value)}
          className={`rounded-full px-4 py-1.5 text-sm font-semibold transition sm:px-6 ${
            value === o.value ? "bg-brand text-white shadow-sm dark:text-[#10201a]" : "text-muted hover:text-ink"
          }`}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

export function SelectPill<T extends string>({
  value, onChange, options,
}: { value: T; onChange: (v: T) => void; options: { value: T; label: string }[] }) {
  return (
    <label className="relative inline-flex items-center">
      <select
        value={value}
        onChange={(e) => onChange(e.target.value as T)}
        className="appearance-none rounded-xl border border-line bg-surface py-2 pl-4 pr-9 text-sm font-semibold outline-none focus:border-brand"
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
      <ChevronDown size={16} className="pointer-events-none absolute right-3 text-muted" />
    </label>
  );
}

export function Field({ label, children, hint }: { label: string; children: ReactNode; hint?: ReactNode }) {
  return (
    <label className="block">
      <span className="label">{label}</span>
      {children}
      {hint && <span className="mt-1 block text-xs text-muted">{hint}</span>}
    </label>
  );
}

export function ChangeBadge({ pct }: { pct: number | null }) {
  if (pct === null || pct === undefined) return null;
  const up = pct > 0;
  const zero = pct === 0;
  return (
    <span className="text-xs font-semibold text-muted" title={t("Bir önceki ölçüme göre değişim")}>
      {zero ? "→" : up ? "↑" : "↓"} {Math.abs(pct).toLocaleString(locale(), { maximumFractionDigits: 1 })}%
    </span>
  );
}
