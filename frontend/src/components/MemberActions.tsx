import { Download, Plus, Trash2 } from "lucide-react";
import { t } from "../lib/i18n";
import { useMemo, useState } from "react";
import { api, withLang, type Summary, type TestDef } from "../lib/api";
import { catLabel, todayISO } from "../lib/format";
import { useApi } from "../lib/hooks";
import { ErrorBox, Field, Modal } from "./ui";

export function ManualEntryModal({ memberId, open, onClose, onSaved }: { memberId: string; open: boolean; onClose: () => void; onSaved: () => void }) {
  const { data: cat } = useApi<{ items: TestDef[] }>(open ? `/api/app/catalog` : null);
  const [date, setDate] = useState(todayISO());
  const [time, setTime] = useState("09:00");
  const [note, setNote] = useState("");
  const [rows, setRows] = useState([{ test_key: "vital.bp_sys", value: "", reference: "" }, { test_key: "vital.bp_dia", value: "", reference: "" }]);
  const [err, setErr] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const tests = useMemo(() => {
    const items = cat?.items ?? [];
    return [...items.filter((tx) => tx.category === "Ölçümler"), ...items.filter((tx) => tx.category !== "Ölçümler")];
  }, [cat]);
  const save = async () => {
    setErr(null);
    setBusy(true);
    try {
      await api(`/api/app/members/${memberId}/manual`, {
        body: { date, time, note: note || null, items: rows.filter((r) => r.value.trim()).map((r) => ({ test_key: r.test_key, value: r.value, reference: r.reference || null })) },
      });
      onSaved();
      onClose();
      setRows([{ test_key: "vital.bp_sys", value: "", reference: "" }, { test_key: "vital.bp_dia", value: "", reference: "" }]);
      setNote("");
    } catch (e) {
      setErr(e);
    } finally {
      setBusy(false);
    }
  };
  return (
    <Modal open={open} onClose={onClose} title={t("Elle değer girişi")}
      footer={<><button className="btn-ghost" onClick={onClose}>{t("Vazgeç")}</button><button className="btn-primary" disabled={busy || !rows.some((r) => r.value.trim())} onClick={save}>{t("Kaydet")}</button></>}>
      <div className="space-y-3">
        <p className="text-sm text-muted">{t("Evde ölçülen tansiyon, kilo, şeker gibi değerler için. Aynı gün ve saatte aynı test iki kez girilemez.")}</p>
        <div className="grid grid-cols-2 gap-3">
          <Field label={t("Tarih")}><input type="date" className="input" value={date} onChange={(e) => setDate(e.target.value)} /></Field>
          <Field label={t("Saat")}><input type="time" className="input" value={time} onChange={(e) => setTime(e.target.value)} /></Field>
        </div>
        {rows.map((r, i) => (
          <div key={i} className="grid grid-cols-[1fr_90px_110px_auto] items-end gap-2">
            <Field label={i === 0 ? t("Test") : ""}>
              <select className="input" value={r.test_key} onChange={(e) => setRows(rows.map((x, j) => (j === i ? { ...x, test_key: e.target.value } : x)))}>
                {tests.map((tx) => <option key={tx.key} value={tx.key}>{tx.display_name}{tx.canonical_unit ? ` (${tx.canonical_unit})` : ""}</option>)}
              </select>
            </Field>
            <Field label={i === 0 ? t("Değer") : ""}><input className="input" value={r.value} onChange={(e) => setRows(rows.map((x, j) => (j === i ? { ...x, value: e.target.value } : x)))} /></Field>
            <Field label={i === 0 ? t("Referans") : ""}><input className="input" placeholder={t("ör. 90 - 130")} value={r.reference} onChange={(e) => setRows(rows.map((x, j) => (j === i ? { ...x, reference: e.target.value } : x)))} /></Field>
            <button className="mb-1 rounded-full p-2 text-muted hover:bg-badbg hover:text-bad" onClick={() => setRows(rows.filter((_, j) => j !== i))} aria-label={t("Satırı sil")}><Trash2 size={15} /></button>
          </div>
        ))}
        <button className="btn-ghost btn-sm" onClick={() => setRows([...rows, { test_key: "vital.weight", value: "", reference: "" }])}><Plus size={14} /> {" "}{t("Satır ekle")}</button>
        <Field label={t("Not (isteğe bağlı)")}><input className="input" value={note} onChange={(e) => setNote(e.target.value)} /></Field>
        <ErrorBox error={err} />
      </div>
    </Modal>
  );
}

export function ExportModal({ memberId, open, onClose, preselect }: { memberId: string; open: boolean; onClose: () => void; preselect?: string[] }) {
  const { data } = useApi<Summary>(open ? `/api/app/members/${memberId}/summary` : null);
  const [sel, setSel] = useState<string[]>(preselect ?? []);
  const items = data?.items ?? [];
  const toggle = (k: string) => setSel((s) => (s.includes(k) ? s.filter((x) => x !== k) : [...s, k]));
  const qs = `tests=${encodeURIComponent(sel.join(","))}`;
  return (
    <Modal open={open} onClose={onClose} title={t("Doktor için dışa aktar")}
      footer={<>
        <a className="btn-ghost" href={withLang(`/api/app/members/${memberId}/export.csv?${qs}`)}><Download size={15} /> {" "}{t("CSV")}</a>
        <a className="btn-primary" href={withLang(`/api/app/members/${memberId}/export.pdf?${qs}`)}><Download size={15} /> {sel.length ? t("PDF ({n} test)", { n: sel.length }) : t("PDF (tüm testler)")}</a>
      </>}>
      <p className="mb-3 text-sm text-muted">{t("Hiçbir test seçmezseniz PDF ve CSV'de tüm testler yer alır (ana sayfadaki sırayla, kategori kategori, gerektiği kadar sayfa). İsterseniz yalnızca bazılarını seçin.")}</p>
      <div className="mb-2 flex gap-2">
        <button className="btn-ghost btn-sm" onClick={() => setSel(items.filter((i) => ["high", "low", "abnormal"].includes(i.latest.flag_computed)).map((i) => i.test_key))}>{t("Referans dışı olanlar")}</button>
        <button className="btn-ghost btn-sm" onClick={() => setSel([])}>{t("Temizle")}</button>
      </div>
      <div className="grid max-h-[50vh] gap-1 overflow-y-auto sm:grid-cols-2">
        {items.map((i) => (
          <label key={i.test_key} className="flex items-center gap-2 rounded-lg px-2 py-1.5 text-sm hover:bg-surface2">
            <input type="checkbox" checked={sel.includes(i.test_key)} onChange={() => toggle(i.test_key)} />
            <span className="truncate">{i.display_name}</span>
            <span className="ml-auto text-xs text-muted">{catLabel(i.category)}</span>
          </label>
        ))}
      </div>
    </Modal>
  );
}
