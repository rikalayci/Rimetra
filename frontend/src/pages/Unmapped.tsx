import { EyeOff, Link2, Plus, Undo2, Unlink } from "lucide-react";
import { t } from "../lib/i18n";
import { useMemo, useState } from "react";
import { Empty, ErrorBox, Field, Modal, Spinner } from "../components/ui";
import { api, type TestDef } from "../lib/api";
import { fmtDate, SPECIMEN_LABEL } from "../lib/format";
import { useApi } from "../lib/hooks";

function NewTestModal({ group, open, onClose, onDone, categories }: { group: any; open: boolean; onClose: () => void; onDone: () => void; categories: string[] }) {
  const slug = (s: string) => s.toLocaleLowerCase("tr-TR").normalize("NFKD").replace(/[ıİ]/g, "i").replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "");
  const sp = group?.specimen ?? "serum";
  const [form, setForm] = useState({ key: `${sp}.${slug(group?.raw_name ?? "")}`, display_name: group?.raw_name ?? "", specimen: sp, category: "Biyokimya", canonical_unit: group?.example_unit ?? "", value_type: "numeric" });
  const [err, setErr] = useState<any>(null);
  const save = async () => {
    setErr(null);
    try {
      await api(`/api/app/catalog/tests?link_raw_name=${encodeURIComponent(group.raw_name)}`, { body: { ...form, canonical_unit: form.canonical_unit || null } });
      onDone();
      onClose();
    } catch (e) {
      setErr(e);
    }
  };
  const set = (k: string, v: string) => {
    if (k === "specimen") {
      // anahtar hâlâ "eskiNumune.ad" biçimindeyse ön eki yeni numuneyle değiştir
      const prefix = `${form.specimen}.`;
      const key = form.key.startsWith(prefix) ? `${v}.${form.key.slice(prefix.length)}` : form.key;
      setForm({ ...form, specimen: v, key });
      return;
    }
    setForm({ ...form, [k]: v });
  };
  return (
    <Modal open={open} onClose={onClose} title={t("Yeni test tanımı")} footer={<><button className="btn-ghost" onClick={onClose}>{t("Vazgeç")}</button><button className="btn-primary" onClick={save}>{t("Oluştur ve bağla")}</button></>}>
      <div className="grid gap-3 sm:grid-cols-2">
        <Field label={t("Görünen ad")}><input className="input" value={form.display_name} onChange={(e) => set("display_name", e.target.value)} /></Field>
        <Field label={t("Anahtar")} hint={t("numune.ad biçiminde, ör. serum.homocysteine")}><input className="input font-mono" value={form.key} onChange={(e) => set("key", e.target.value)} /></Field>
        <Field label={t("Numune")}>
          <select className="input" value={form.specimen} onChange={(e) => set("specimen", e.target.value)}>
            {["blood", "serum", "plasma", "urine", "other"].map((s) => <option key={s} value={s}>{SPECIMEN_LABEL[s]}</option>)}
          </select>
        </Field>
        <Field label={t("Kategori")}>
          <input className="input" list="cats" value={form.category} onChange={(e) => set("category", e.target.value)} />
          <datalist id="cats">{categories.map((c) => <option key={c} value={c} />)}</datalist>
        </Field>
        <Field label={t("Birim")}><input className="input" value={form.canonical_unit} onChange={(e) => set("canonical_unit", e.target.value)} /></Field>
        <Field label={t("Değer tipi")}>
          <select className="input" value={form.value_type} onChange={(e) => set("value_type", e.target.value)}>
            <option value="numeric">{t("Sayısal")}</option><option value="qualitative">{t("Nitel")}</option><option value="text">{t("Metin")}</option>
          </select>
        </Field>
      </div>
      <div className="mt-3"><ErrorBox error={err} /></div>
    </Modal>
  );
}

export default function Unmapped() {
  const { data, loading, reload } = useApi<{ items: any[] }>("/api/app/unmapped");
  const { data: cat } = useApi<{ items: TestDef[]; categories: string[] }>("/api/app/catalog");
  const [choice, setChoice] = useState<Record<string, string>>({});
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<any>(null);
  const [newFor, setNewFor] = useState<any>(null);
  const [undo, setUndo] = useState<{ ids: string[]; label: string } | null>(null);
  const tests = cat?.items ?? [];
  const bySpec = useMemo(() => (sp: string | null) => {
    const blood = ["blood", "serum", "plasma"];
    return tests.filter((tx) => !sp || tx.specimen === sp || (blood.includes(sp) && blood.includes(tx.specimen)));
  }, [tests]);

  const link = async (g: any) => {
    const key = choice[g.raw_name + g.specimen] || g.suggestions?.[0]?.key;
    if (!key) return;
    setErr(null);
    try {
      const r = await api("/api/app/catalog/aliases", { body: { raw_name: g.raw_name, specimen: g.specimen ?? "serum", test_key: key } });
      setMsg(t("\"{name}\" → {key} bağlandı ({n} sonuç{extra}).", { name: g.raw_name, key, n: r.linked_results, extra: r.conflicts ? t(", {n} çakışma atlandı", { n: r.conflicts }) : "" }));
      reload();
    } catch (e) {
      setErr(e);
    }
  };

  // "Sonuç değil": istem satırı gibi sonuç olmayan satırları gizler (kalıcı silmez, geri alınabilir)
  const dismiss = async (g: any) => {
    setErr(null);
    setMsg(null);
    try {
      const r = await api("/api/app/unmapped/dismiss", { body: { raw_name: g.raw_name, specimen: g.specimen ?? null, reason: "Arayüzden: sonuç değil" } });
      setUndo({ ids: r.results.map((x: any) => x.result_id), label: t("\"{name}\" gizlendi ({n} satır).", { name: g.raw_name, n: r.dismissed_count }) });
      reload();
    } catch (e) {
      setErr(e);
    }
  };

  const restore = async () => {
    if (!undo) return;
    setErr(null);
    try {
      await api("/api/app/results/restore", { body: { result_ids: undo.ids } });
      setUndo(null);
      reload();
    } catch (e) {
      setErr(e);
    }
  };

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-[36px] font-extrabold tracking-tight">{t("Eşleşmemiş testler")}</h1>
        <p className="max-w-3xl text-muted">{t("Ajanın gönderdiği ama kataloğa eşlenemeyen test adları. Bir standart teste bağladığınızda bu ad gelecekte de otomatik eşlenir ve mevcut sonuçlar trendlere katılır. Sonuç olmayan satırları (ör. istem satırı “Kan Sayımı … : 1”)")}{" "}<EyeOff size={14} className="inline align-[-2px]" /> {" "}{t("ile gizleyebilirsiniz.")}</p>
      </div>
      {msg && <div className="rounded-xl bg-okbg px-3 py-2 text-sm text-ok">{msg}</div>}
      {undo && (
        <div className="flex items-center justify-between gap-3 rounded-xl bg-surface2 px-3 py-2 text-sm">
          <span>{undo.label} {" "}{t("Rapor ve PDF değişmedi.")}</span>
          <button className="btn-ghost btn-sm" onClick={restore}><Undo2 size={14} /> {" "}{t("Geri al")}</button>
        </div>
      )}
      <ErrorBox error={err} />
      {loading && !data ? <Spinner /> : !data?.items.length ? (
        <Empty title={t("Eşleşmemiş test yok")} icon={<Unlink className="text-muted" />}>{t("Tüm sonuçlar kataloğa bağlı.")}</Empty>
      ) : (
        <div className="card overflow-x-auto">
          <table className="table-clean w-full min-w-[900px]">
            <thead className="bg-surface2"><tr><th>{t("Ham ad")}</th><th>{t("Numune")}</th><th>{t("Örnek")}</th><th>{t("Adet")}</th><th>{t("Son")}</th><th className="w-[400px]">{t("Bağla")}</th></tr></thead>
            <tbody>
              {data.items.map((g) => {
                const k = g.raw_name + g.specimen;
                return (
                  <tr key={k}>
                    <td className="font-semibold">{g.raw_name}</td>
                    <td>{SPECIMEN_LABEL[g.specimen] ?? "—"}</td>
                    <td className="text-muted">{g.example_value} {g.example_unit ?? ""}</td>
                    <td>{g.count}</td>
                    <td className="text-muted">{fmtDate(g.last_seen)}</td>
                    <td>
                      <div className="flex gap-2">
                        <select className="input" value={choice[k] ?? g.suggestions?.[0]?.key ?? ""} onChange={(e) => setChoice({ ...choice, [k]: e.target.value })}>
                          <option value="">{t("Test seçin…")}</option>
                          {g.suggestions?.length > 0 && <optgroup label={t("Öneriler")}>{g.suggestions.map((s: any) => <option key={"s" + s.key} value={s.key}>{s.display_name}</option>)}</optgroup>}
                          <optgroup label={t("Tümü")}>{bySpec(g.specimen).map((tx) => <option key={tx.key} value={tx.key}>{tx.display_name} ({tx.key})</option>)}</optgroup>
                        </select>
                        <button className="btn-primary btn-sm" onClick={() => link(g)}><Link2 size={14} /> {" "}{t("Bağla")}</button>
                        <button className="btn-ghost btn-sm" onClick={() => setNewFor(g)} title={t("Yeni test tanımı")}><Plus size={14} /></button>
                        <button className="btn-ghost btn-sm" onClick={() => dismiss(g)} title={t("Sonuç değil — {n} satırı gizle (geri alınabilir)", { n: g.count })}><EyeOff size={14} /></button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
      {newFor && <NewTestModal key={newFor.raw_name} group={newFor} open onClose={() => setNewFor(null)} onDone={reload} categories={cat?.categories ?? []} />}
    </div>
  );
}
