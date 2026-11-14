import { Bell, Plus, StickyNote, Trash2 } from "lucide-react";
import { t } from "../lib/i18n";
import { useState } from "react";
import { api, type Note, type TestDef } from "../lib/api";
import { useAuth } from "../lib/auth";
import { catLabel, fmtDate, todayISO } from "../lib/format";
import { useApi } from "../lib/hooks";
import { Empty, ErrorBox, Spinner } from "./ui";

export function NotesTab({ memberId }: { memberId: string }) {
  const { me } = useAuth();
  const { data, loading, reload } = useApi<{ items: Note[] }>(`/api/app/members/${memberId}/notes`);
  const { data: cat } = useApi<{ items: TestDef[] }>(`/api/app/catalog`);
  const [date, setDate] = useState(todayISO());
  const [text, setText] = useState("");
  const [testKey, setTestKey] = useState("");
  const [err, setErr] = useState<any>(null);
  const canWrite = me?.role === "master" || (me?.member_id === memberId && !me?.read_only);

  const add = async () => {
    setErr(null);
    try {
      await api(`/api/app/members/${memberId}/notes`, { body: { date, text, test_key: testKey || null } });
      setText("");
      setTestKey("");
      reload();
    } catch (e) {
      setErr(e);
    }
  };
  const del = async (id: string) => {
    if (!confirm(t("Not silinsin mi?"))) return;
    await api(`/api/app/notes/${id}`, { method: "DELETE" });
    reload();
  };

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_360px]">
      <div>
        {loading && !data ? <Spinner /> : !data?.items.length ? (
          <Empty title={t("Henüz not yok")} icon={<StickyNote className="text-muted" />}>
            {t("\"İlaç başladı\", \"diyet değişti\" gibi olayları ekleyin; test grafiklerinde işaret olarak görünür.")}</Empty>
        ) : (
          <ol className="relative space-y-3 border-l-2 border-dashed border-line pl-5">
            {data.items.map((n) => (
              <li key={n.id} className="relative">
                <span className="absolute -left-[29px] top-4 h-3.5 w-3.5 rounded-full border-2 border-surface bg-[#D9934A]" />
                <div className="card flex items-start gap-3 px-4 py-3">
                  <div className="min-w-[92px] text-sm font-bold">{fmtDate(n.date)}</div>
                  <div className="flex-1">
                    <div className="whitespace-pre-wrap text-[15px]">{n.text}</div>
                    {n.test_name && <div className="mt-1 text-xs text-muted">{t("İlgili test:")}{" "}{n.test_name}</div>}
                  </div>
                  {n.can_delete && (
                    <button onClick={() => del(n.id)} className="rounded-full p-1.5 text-muted hover:bg-badbg hover:text-bad" aria-label={t("Sil")}><Trash2 size={15} /></button>
                  )}
                </div>
              </li>
            ))}
          </ol>
        )}
      </div>
      <div className="space-y-4">
        {canWrite && (
          <div className="card space-y-3 p-4">
            <div className="font-bold">{t("Not / olay ekle")}</div>
            <input type="date" className="input" value={date} onChange={(e) => setDate(e.target.value)} />
            <textarea className="input min-h-[84px]" placeholder={t("Ör. Diyet değişti")} value={text} onChange={(e) => setText(e.target.value)} />
            <select className="input" value={testKey} onChange={(e) => setTestKey(e.target.value)}>
              <option value="">{t("Tüm testler için (genel)")}</option>
              {cat?.items.map((tx) => <option key={tx.key} value={tx.key}>{tx.display_name} · {catLabel(tx.category)}</option>)}
            </select>
            <ErrorBox error={err} />
            <button className="btn-primary w-full" onClick={add} disabled={!text.trim()}><Plus size={16} /> {" "}{t("Ekle")}</button>
          </div>
        )}
        <Reminders memberId={memberId} catalog={cat?.items ?? []} />
      </div>
    </div>
  );
}

function Reminders({ memberId, catalog }: { memberId: string; catalog: TestDef[] }) {
  const { me } = useAuth();
  const { data, reload } = useApi<{ items: any[] }>(`/api/app/members/${memberId}/reminders`);
  const [key, setKey] = useState("");
  const [months, setMonths] = useState(6);
  const master = me?.role === "master";
  const add = async () => {
    await api(`/api/app/members/${memberId}/reminders`, { body: { test_key: key, interval_months: months } });
    setKey("");
    reload();
  };
  const del = async (id: string) => {
    await api(`/api/app/reminders/${id}`, { method: "DELETE" });
    reload();
  };
  const label: Record<string, string> = { due: t("Zamanı geldi"), never: t("Hiç yapılmadı"), soon: t("Yaklaşıyor"), ok: t("Planlı") };
  const cls: Record<string, string> = { due: "bg-badbg text-bad", never: "bg-warnbg text-warn", soon: "bg-warnbg text-warn", ok: "bg-okbg text-ok" };
  return (
    <div className="card space-y-3 p-4">
      <div className="flex items-center gap-2 font-bold"><Bell size={17} /> {" "}{t("Kontrol hatırlatıcıları")}</div>
      {!data?.items.length && <div className="text-sm text-muted">{t("Hatırlatıcı yok.")}</div>}
      {data?.items.map((r) => (
        <div key={r.id} className="flex items-center gap-2 text-sm">
          <div className="flex-1">
            <div className="font-semibold">{r.display_name} <span className="font-normal text-muted">· {r.interval_months} {" "}{t("ayda bir")}</span></div>
            <div className="text-xs text-muted">{t("Son:")}{" "}{r.last_done ? fmtDate(r.last_done) : "—"} {" "}{t("· Sıradaki:")}{" "}{fmtDate(r.due_date)}</div>
          </div>
          <span className={`chip ${cls[r.status]}`}>{label[r.status]}</span>
          {master && <button onClick={() => del(r.id)} className="text-muted hover:text-bad" aria-label={t("Sil")}><Trash2 size={14} /></button>}
        </div>
      ))}
      {master && (
        <div className="flex flex-wrap gap-2 border-t border-line pt-3">
          <select className="input flex-1" value={key} onChange={(e) => setKey(e.target.value)}>
            <option value="">{t("Test seçin…")}</option>
            {catalog.map((tx) => <option key={tx.key} value={tx.key}>{tx.display_name}</option>)}
          </select>
          <select className="input w-28" value={months} onChange={(e) => setMonths(+e.target.value)}>
            {[1, 3, 6, 12, 24].map((m) => <option key={m} value={m}>{m} {" "}{t("ay")}</option>)}
          </select>
          <button className="btn-ghost btn-sm" disabled={!key} onClick={add}><Plus size={14} /> {" "}{t("Ekle")}</button>
        </div>
      )}
    </div>
  );
}
