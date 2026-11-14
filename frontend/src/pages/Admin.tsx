import { Copy, Database, Download, Info, KeyRound, Pencil, Plus, ScrollText, Send, Trash2, Upload, Users, Plug, BookOpen } from "lucide-react";
import { t } from "../lib/i18n";
import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { AgentGuide } from "../components/AgentGuide";
import { BotSetupSteps, type TelegramStatus } from "../components/TelegramConnect";
import { Avatar } from "../components/Avatar";
import { Empty, ErrorBox, Field, Modal, Spinner } from "../components/ui";
import { infoLabels } from "../components/TestInfo";
import { api, type Member, type TestDef } from "../lib/api";
import { AVATAR_COLORS, catLabel, fmtDateTime, SPECIMEN_LABEL } from "../lib/format";
import { useApi } from "../lib/hooks";

const TABS = [
  { id: "uyeler", get label() { return t("Üyeler"); }, icon: Users },
  { id: "anahtarlar", get label() { return t("API anahtarları"); }, icon: KeyRound },
  { id: "baglanti", get label() { return t("Ajan bağlantısı (MCP)"); }, icon: Plug },
  { id: "telegram", get label() { return t("Telegram botu"); }, icon: Send },
  { id: "katalog", get label() { return t("Test kataloğu"); }, icon: BookOpen },
  { id: "denetim", get label() { return t("Denetim kaydı"); }, icon: ScrollText },
  { id: "yedek", get label() { return t("Yedekleme"); }, icon: Database },
];

// ------------------------------------------------------------------ üyeler + hesaplar

function MemberForm({ member, open, onClose, onSaved }: { member: Member | null; open: boolean; onClose: () => void; onSaved: () => void }) {
  const [f, setF] = useState({
    display_name: member?.display_name ?? "", full_name: member?.full_name ?? "", sex: member?.sex ?? "",
    birth_year: member?.birth_year?.toString() ?? "", avatar_color: member?.avatar_color ?? "",
  });
  const [login, setLogin] = useState({ enabled: false, username: "", password: "", read_only: false });
  const [err, setErr] = useState<any>(null);
  const save = async () => {
    setErr(null);
    const body = { display_name: f.display_name, full_name: f.full_name || null, sex: f.sex || null,
      birth_year: f.birth_year ? +f.birth_year : null, avatar_color: f.avatar_color || null };
    try {
      let m: Member;
      if (member) m = await api(`/api/app/members/${member.id}`, { method: "PATCH", body });
      else m = await api(`/api/app/members`, { body });
      if (!member && login.enabled) {
        await api(`/api/app/admin/users`, { body: { username: login.username, password: login.password, member_id: m.id, role: "member", read_only: login.read_only } });
      }
      onSaved();
      onClose();
    } catch (e) {
      setErr(e);
    }
  };
  return (
    <Modal open={open} onClose={onClose} title={member ? t("Üyeyi düzenle") : t("Yeni üye / profil")}
      footer={<><button className="btn-ghost" onClick={onClose}>{t("Vazgeç")}</button><button className="btn-primary" onClick={save} disabled={!f.display_name.trim()}>{t("Kaydet")}</button></>}>
      <div className="space-y-3">
        <Field label={t("Görünen ad")}><input className="input" value={f.display_name} onChange={(e) => setF({ ...f, display_name: e.target.value })} placeholder={t("Ayşe")} /></Field>
        <Field label={t("Belgedeki ad soyad")} hint={t("e-Nabız PDF'indeki 'Adı/Soyadı' ile karşılaştırılır (isim uyuşmazlığı kontrolü). TC kimlik no girmeyin.")}>
          <input className="input" value={f.full_name} onChange={(e) => setF({ ...f, full_name: e.target.value })} placeholder={t("AYŞE YILMAZ")} />
        </Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label={t("Cinsiyet")}>
            <select className="input" value={f.sex} onChange={(e) => setF({ ...f, sex: e.target.value })}><option value="">—</option><option value="F">{t("Kadın")}</option><option value="M">{t("Erkek")}</option></select>
          </Field>
          <Field label={t("Doğum yılı")}><input className="input" inputMode="numeric" value={f.birth_year} onChange={(e) => setF({ ...f, birth_year: e.target.value.replace(/\D/g, "").slice(0, 4) })} /></Field>
        </div>
        <Field label={t("Avatar rengi")}>
          <div className="flex gap-2">
            {AVATAR_COLORS.map((c) => (
              <button key={c} onClick={() => setF({ ...f, avatar_color: c })} className={`h-8 w-8 rounded-full border-2 ${f.avatar_color === c ? "border-brand" : "border-transparent"}`} style={{ background: c }} aria-label={c} />
            ))}
          </div>
        </Field>
        {!member && (
          <div className="rounded-xl border border-line p-3">
            <label className="flex items-center gap-2 text-sm font-semibold"><input type="checkbox" checked={login.enabled} onChange={(e) => setLogin({ ...login, enabled: e.target.checked })} /> {" "}{t("Bu kişi giriş yapabilsin")}</label>
            <p className="mt-1 text-xs text-muted">{t("İşaretlemezseniz girişsiz profil olur (çocuk, yaşlı ebeveyn vb.). Verisini siz yönetirsiniz.")}</p>
            {login.enabled && (
              <div className="mt-3 grid gap-3 sm:grid-cols-2">
                <Field label={t("Kullanıcı adı")}><input className="input" value={login.username} onChange={(e) => setLogin({ ...login, username: e.target.value })} /></Field>
                <Field label={t("Şifre")}><input className="input" type="password" value={login.password} onChange={(e) => setLogin({ ...login, password: e.target.value })} /></Field>
                <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={login.read_only} onChange={(e) => setLogin({ ...login, read_only: e.target.checked })} /> {" "}{t("Salt okunur (not ekleyemez)")}</label>
              </div>
            )}
          </div>
        )}
        <ErrorBox error={err} />
      </div>
    </Modal>
  );
}

function AccountModal({ member, user, open, onClose, onSaved }: { member: Member; user: any | null; open: boolean; onClose: () => void; onSaved: () => void }) {
  const [username, setU] = useState(user?.username ?? "");
  const [password, setP] = useState("");
  const [ro, setRo] = useState(user?.read_only ?? false);
  const [active, setActive] = useState(user?.is_active ?? true);
  const [tgId, setTgId] = useState<string>(user?.telegram_chat_id ? String(user.telegram_chat_id) : "");
  const [err, setErr] = useState<any>(null);
  const save = async () => {
    setErr(null);
    try {
      const tgChange: Record<string, any> = {};
      const tgNew = tgId.trim() ? Number(tgId.trim()) : null;
      if (user && tgNew !== (user.telegram_chat_id ?? null)) tgChange.telegram_chat_id = tgNew;
      if (user) await api(`/api/app/admin/users/${user.id}`, { method: "PATCH", body: { read_only: ro, is_active: active, ...tgChange, ...(password ? { password } : {}) } });
      else await api(`/api/app/admin/users`, { body: { username, password, member_id: member.id, role: "member", read_only: ro } });
      onSaved();
      onClose();
    } catch (e) {
      setErr(e);
    }
  };
  const remove = async () => {
    if (!user || !confirm(t("Giriş hesabı silinsin mi? (Profil ve veriler kalır)"))) return;
    await api(`/api/app/admin/users/${user.id}`, { method: "DELETE" });
    onSaved();
    onClose();
  };
  return (
    <Modal open={open} onClose={onClose} title={t("{name} · giriş hesabı", { name: member.display_name })}
      footer={<>{user && user.role !== "master" && <button className="btn-ghost mr-auto text-bad" onClick={remove}>{t("Hesabı sil")}</button>}<button className="btn-ghost" onClick={onClose}>{t("Vazgeç")}</button><button className="btn-primary" onClick={save}>{t("Kaydet")}</button></>}>
      <div className="space-y-3">
        <Field label={t("Kullanıcı adı")}><input className="input" value={username} disabled={!!user} onChange={(e) => setU(e.target.value)} /></Field>
        <Field label={user ? t("Yeni şifre (boş bırakılırsa değişmez)") : t("Şifre")}><input className="input" type="password" value={password} onChange={(e) => setP(e.target.value)} /></Field>
        {user?.role !== "master" && <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={ro} onChange={(e) => setRo(e.target.checked)} /> {" "}{t("Salt okunur")}</label>}
        {user && user.role !== "master" && <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={active} onChange={(e) => setActive(e.target.checked)} /> {" "}{t("Aktif")}</label>}
        {user && (
          <Field label={t("Telegram ID (isteğe bağlı)")} hint={<>{t("Kişi bota yazınca bot ona ID'sini söyler. Boş bırakılırsa Telegram bağlantısı kaldırılır. Kişi kendisi de profil menüsünden")}{" "}<b>{t("Telegram'ı bağla")}</b> {" "}{t("ile tek dokunuşla bağlayabilir.")}{user.telegram?.username && <> {" "}{t("Şu an bağlı: @")}{user.telegram.username}</>}</>}>
            <input className="input font-mono" inputMode="numeric" placeholder={t("ör. 123456789")} value={tgId} onChange={(e) => setTgId(e.target.value.replace(/[^0-9]/g, ""))} />
          </Field>
        )}
        <ErrorBox error={err} />
      </div>
    </Modal>
  );
}

function MembersTab() {
  const { data, loading, reload } = useApi<{ items: Member[] }>("/api/app/members");
  const { data: users, reload: reloadUsers } = useApi<{ items: any[] }>("/api/app/admin/users");
  const [edit, setEdit] = useState<Member | null | "new">(null);
  const [acct, setAcct] = useState<Member | null>(null);
  const [del, setDel] = useState<Member | null>(null);
  const [confirmName, setConfirm] = useState("");
  const [err, setErr] = useState<any>(null);
  const userOf = (m: Member) => users?.items.find((u) => u.member_id === m.id) ?? null;
  const refresh = () => { reload(); reloadUsers(); };

  const upload = async (m: Member, f: File) => {
    const fd = new FormData();
    fd.append("file", f);
    try {
      await api(`/api/app/members/${m.id}/avatar`, { form: fd });
      reload();
    } catch (e) {
      setErr(e);
    }
  };
  const doDelete = async () => {
    if (!del) return;
    try {
      await api(`/api/app/members/${del.id}?confirm=${encodeURIComponent(confirmName)}`, { method: "DELETE" });
      setDel(null);
      setConfirm("");
      refresh();
    } catch (e) {
      setErr(e);
    }
  };

  if (loading && !data) return <Spinner />;
  return (
    <div className="space-y-4">
      <div className="flex items-center"><p className="text-sm text-muted">{t("Profiller (girişli veya girişsiz). Her profile en fazla bir giriş hesabı bağlanır.")}</p>
        <button className="btn-primary ml-auto" onClick={() => setEdit("new")}><Plus size={16} /> {" "}{t("Üye ekle")}</button></div>
      <ErrorBox error={err} />
      <div className="grid gap-3 md:grid-cols-2">
        {data?.items.map((m) => {
          const u = userOf(m);
          return (
            <div key={m.id} className="card flex items-center gap-4 p-4">
              <label className="group relative cursor-pointer" title={t("Fotoğraf yükle")}>
                <Avatar member={m} size={64} />
                <span className="absolute inset-0 hidden items-center justify-center rounded-full bg-black/40 text-white group-hover:flex"><Upload size={18} /></span>
                <input type="file" accept="image/png,image/jpeg,image/webp" className="hidden" onChange={(e) => e.target.files?.[0] && upload(m, e.target.files[0])} />
              </label>
              <div className="min-w-0 flex-1">
                <div className="text-lg font-bold">{m.display_name}</div>
                <div className="truncate text-xs text-muted">{m.full_name ?? t("Belge adı yok")} · {m.birth_year ?? "—"} · <span className="font-mono">{m.id}</span></div>
                <div className="mt-1 text-xs">
                  {u ? <span className="chip bg-okbg text-ok">@{u.username} · {u.role === "master" ? t("Yönetici") : u.read_only ? "salt okunur" : t("üye")}{!u.is_active && t(" · pasif")}</span> : <span className="chip bg-surface2 text-muted">{t("Girişsiz profil")}</span>}
                  {u?.telegram?.linked && <span className="chip ml-1 bg-[#2AABEE]/15 text-[#1c8fcc]"><Send size={11} /> {" "}{t("Telegram")}</span>}
                </div>
              </div>
              <div className="flex flex-col gap-1">
                <button className="btn-ghost btn-sm" onClick={() => setEdit(m)}><Pencil size={13} /> {" "}{t("Düzenle")}</button>
                <button className="btn-ghost btn-sm" onClick={() => setAcct(m)}><KeyRound size={13} /> {" "}{t("Hesap")}</button>
                {u?.role !== "master" && <button className="btn-ghost btn-sm text-bad" onClick={() => { setDel(m); setConfirm(""); }}><Trash2 size={13} /> {" "}{t("Sil")}</button>}
              </div>
            </div>
          );
        })}
      </div>
      {edit && <MemberForm member={edit === "new" ? null : edit} open onClose={() => setEdit(null)} onSaved={refresh} />}
      {acct && <AccountModal member={acct} user={userOf(acct)} open onClose={() => setAcct(null)} onSaved={refresh} />}
      <Modal open={!!del} onClose={() => setDel(null)} title={t("Üyeyi ve tüm verisini sil")}
        footer={<><button className="btn-ghost" onClick={() => setDel(null)}>{t("Vazgeç")}</button><button className="btn-danger" disabled={confirmName.trim() === ""} onClick={doDelete}>{t("Kalıcı olarak sil")}</button></>}>
        <p className="text-sm">{t("Bu işlem")}{" "}<b>{del?.display_name}</b> {" "}{t("profilini, tüm raporlarını, PDF'lerini, notlarını ve giriş hesabını kalıcı olarak siler. Geri alınamaz.")}</p>
        <Field label={t("Onaylamak için \"{name}\" yazın", { name: del?.display_name })}><input className="input mt-2" value={confirmName} onChange={(e) => setConfirm(e.target.value)} /></Field>
      </Modal>
    </div>
  );
}

// ------------------------------------------------------------------ API anahtarları

function KeysTab() {
  const { data, reload } = useApi<{ items: any[] }>("/api/app/admin/api-keys");
  const { data: mem } = useApi<{ items: Member[] }>("/api/app/members");
  const { data: meta } = useApi<any>("/api/app/meta");
  const [open, setOpen] = useState(false);
  const [name, setName] = useState(t("Claude ajanı"));
  const [scopes, setScopes] = useState<string[]>(["reports:read", "reports:write", "members:read"]);
  const [limit, setLimit] = useState<string[]>([]);
  const [created, setCreated] = useState<string | null>(null);
  const [err, setErr] = useState<any>(null);
  const create = async () => {
    setErr(null);
    try {
      const r = await api(`/api/app/admin/api-keys`, { body: { name, scopes, member_scope: limit.length ? limit : null } });
      setCreated(r.key);
      setOpen(false);
      reload();
    } catch (e) {
      setErr(e);
    }
  };
  const revoke = async (id: string) => {
    if (!confirm(t("Anahtar iptal edilsin mi? Bu anahtarı kullanan ajan erişimini kaybeder."))) return;
    await api(`/api/app/admin/api-keys/${id}/revoke`, { method: "POST" });
    reload();
  };
  const names = Object.fromEntries((mem?.items ?? []).map((m) => [m.id, m.display_name]));
  return (
    <div className="space-y-4">
      <div className="flex items-center"><p className="text-sm text-muted">{t("Anahtar yalnızca oluşturulurken bir kez gösterilir; veritabanında hash'i saklanır.")}</p>
        <button className="btn-primary ml-auto" onClick={() => setOpen(true)}><Plus size={16} /> {" "}{t("Anahtar oluştur")}</button></div>
      {created && (
        <div className="rounded-2xl border-2 border-brand/50 bg-brandsoft/50 p-4">
          <div className="font-bold">{t("Yeni anahtar — şimdi kopyalayın, bir daha gösterilmeyecek")}</div>
          <div className="mt-2 flex items-center gap-2">
            <code className="flex-1 break-all rounded-lg bg-surface px-3 py-2 font-mono text-sm">{created}</code>
            <button className="btn-ghost btn-sm" onClick={() => navigator.clipboard?.writeText(created)}><Copy size={14} /> {" "}{t("Kopyala")}</button>
          </div>
          <button className="mt-2 text-xs text-muted underline" onClick={() => setCreated(null)}>{t("Kopyaladım, gizle")}</button>
        </div>
      )}
      <div className="card overflow-x-auto">
        <table className="table-clean w-full min-w-[820px]">
          <thead className="bg-surface2"><tr><th>{t("Ad")}</th><th>{t("Önek")}</th><th>{t("Yetkiler")}</th><th>{t("Üye kısıtı")}</th><th>{t("Son kullanım")}</th><th></th></tr></thead>
          <tbody>
            {data?.items.map((k) => (
              <tr key={k.id} className={k.revoked_at ? "opacity-50" : ""}>
                <td className="font-semibold">{k.name}</td>
                <td className="font-mono text-xs">{k.key_prefix}</td>
                <td><div className="flex flex-wrap gap-1">{k.scopes.map((s: string) => <span key={s} className="chip bg-surface2 px-2 py-0.5 text-[11px]">{s}</span>)}</div></td>
                <td className="text-sm">{k.member_scope ? k.member_scope.map((id: string) => names[id] ?? id).join(", ") : t("Tüm üyeler")}</td>
                <td className="text-sm text-muted">{k.last_used_at ? fmtDateTime(k.last_used_at) : t("Hiç")}</td>
                <td>{k.revoked_at ? <span className="chip bg-badbg text-bad">{t("İptal ·")}{" "}{fmtDateTime(k.revoked_at)}</span> : <button className="btn-ghost btn-sm text-bad" onClick={() => revoke(k.id)}>{t("İptal et")}</button>}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {!data?.items.length && <div className="p-6 text-center text-sm text-muted">{t("Henüz anahtar yok.")}</div>}
      </div>
      <Modal open={open} onClose={() => setOpen(false)} title={t("API anahtarı oluştur")}
        footer={<><button className="btn-ghost" onClick={() => setOpen(false)}>{t("Vazgeç")}</button><button className="btn-primary" onClick={create} disabled={!name || !scopes.length}>{t("Oluştur")}</button></>}>
        <div className="space-y-4">
          <Field label={t("Ad")}><input className="input" value={name} onChange={(e) => setName(e.target.value)} /></Field>
          <div>
            <span className="label">{t("Yetkiler")}</span>
            <div className="grid grid-cols-2 gap-1">
              {(meta?.scopes ?? []).map((s: string) => (
                <label key={s} className="flex items-center gap-2 text-sm"><input type="checkbox" checked={scopes.includes(s)} onChange={() => setScopes(scopes.includes(s) ? scopes.filter((x) => x !== s) : [...scopes, s])} /> <code>{s}</code></label>
              ))}
            </div>
          </div>
          <div>
            <span className="label">{t("Üye kısıtı (boşsa tüm üyeler)")}</span>
            <div className="grid grid-cols-2 gap-1">
              {mem?.items.map((m) => (
                <label key={m.id} className="flex items-center gap-2 text-sm"><input type="checkbox" checked={limit.includes(m.id)} onChange={() => setLimit(limit.includes(m.id) ? limit.filter((x) => x !== m.id) : [...limit, m.id])} /> {m.display_name}</label>
              ))}
            </div>
            <p className="mt-1 text-xs text-muted">{t("Üye kısıtlı anahtar yeni üye oluşturamaz ve diğer üyelere yazamaz.")}</p>
          </div>
          <ErrorBox error={err} />
        </div>
      </Modal>
    </div>
  );
}

// ------------------------------------------------------------------ bağlantı bilgisi

function ConnectTab() {
  return <AgentGuide />;
}

// ------------------------------------------------------------------ Telegram botu

function TelegramTab() {
  const { data: st, reload } = useApi<TelegramStatus>("/api/app/telegram");
  const { data: users } = useApi<{ items: any[] }>("/api/app/admin/users");
  if (!st) return <Spinner />;
  const linked = users?.items.filter((u) => u.telegram?.linked) ?? [];
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <div className="card space-y-3 p-5">
        <div className="flex items-center gap-2 text-lg font-bold"><Send size={18} className="text-[#2AABEE]" /> {" "}{t("Bot durumu")}</div>
        {!st.enabled ? (
          <><div className="rounded-xl bg-surface2 px-3 py-2 text-sm">{t("Bot kapalı —")}{" "}<code>TELEGRAM_BOT_TOKEN</code> {" "}{t("tanımlı değil.")}</div><BotSetupSteps /></>
        ) : (
          <>
            <div className="text-sm">
              {st.bot_username ? <>{t("Bot:")}{" "}<a className="font-semibold text-brand underline" href={st.bot_url ?? "#"} target="_blank" rel="noreferrer">@{st.bot_username}</a></> : t("Bot bilgisi alınamadı.")}
              {" · "}{st.running && !st.last_error ? <span className="font-semibold text-ok">{t("çalışıyor")}</span> : <span className="font-semibold text-bad">{t("bağlantı sorunu")}</span>}
            </div>
            {st.last_error && <ErrorBox error={{ message: st.last_error }} />}
            <div className="text-sm text-muted">{t("Yeni tahlil bildirimleri:")}{" "}{st.notify_enabled ? t("açık") : t("kapalı (TELEGRAM_NOTIFY=false)")}</div>
            <button className="btn-ghost btn-sm" onClick={reload}>{t("Yenile")}</button>
          </>
        )}
      </div>
      <div className="card space-y-3 p-5">
        <div className="text-lg font-bold">{t("Kimler bağlı?")}</div>
        {linked.length ? (
          <ul className="space-y-1 text-sm">
            {linked.map((u) => (
              <li key={u.id} className="flex items-center gap-2"><span className="font-semibold">@{u.username}</span>
                <span className="text-muted">{u.telegram.username ? `→ @${u.telegram.username}` : `→ ${u.telegram_chat_id}`}</span>
                {!u.telegram.notify && <span className="chip bg-surface2 text-muted">{t("bildirim kapalı")}</span>}</li>
            ))}
          </ul>
        ) : <div className="text-sm text-muted">{t("Henüz kimse bağlanmadı.")}</div>}
        <div className="rounded-xl bg-surface2 p-3 text-sm">
          <div className="mb-1 font-bold">{t("Nasıl bağlanılır?")}</div>
          <ul className="list-disc space-y-1 pl-5">
            <li><b>{t("En kolayı:")}</b> {" "}{t("herkes kendi hesabıyla giriş yapıp sağ üstteki profil menüsünden")}{" "}<b>{t("Telegram'ı bağla")}</b>{t("'ya dokunur.")}</li>
            <li><b>{t("Yönetici olarak:")}</b> {" "}{t("kişi bota yazınca bot ona Telegram ID'sini söyler; Üyeler →")}{" "}<b>{t("Hesap")}</b> → <b>{t("Telegram ID")}</b> {" "}{t("alanına yazın.")}</li>
          </ul>
          <p className="mt-2 text-xs text-muted">{t("Bot, bağlı hesabın yetkisiyle yanıt verir: yönetici herkesi, üye yalnızca kendi profilini görür. Bot veri değiştirmez. Hesap pasifleşirse bot da yanıt vermeyi keser.")}</p>
        </div>
      </div>
    </div>
  );
}

// ------------------------------------------------------------------ katalog

// Boş bırakılan açıklama: hiç yoksa null kalır, önceden varsa "" kaydedilir
// (böylece kasıtlı silinen yerleşik açıklama açılışta geri yazılmaz).
const infoText = (v: string, prev: string | null | undefined) => v.trim() || (prev == null ? null : "");
/** Düzenleme formu kayıtlı (çevrilmemiş) metinle çalışır; yerleşik metinler ekranda çevrilmiş görünür. */
const raw = (td: TestDef, f: "what" | "low" | "high") => {
  const r = (td as any)[`info_${f}_raw`];
  return r !== undefined ? (r as string | null) : (td as any)[`info_${f}`];
};

function CatalogTab() {
  const { data, reload } = useApi<{ items: TestDef[]; categories: string[] }>("/api/app/catalog");
  const [q, setQ] = useState("");
  const [edit, setEdit] = useState<TestDef | null>(null);
  const [rules, setRules] = useState("");
  const [unit, setUnit] = useState("");
  const [newKey, setNewKey] = useState("");
  const [specimen, setSpecimen] = useState("");
  const [infoWhat, setInfoWhat] = useState("");
  const [infoLow, setInfoLow] = useState("");
  const [infoHigh, setInfoHigh] = useState("");
  const [err, setErr] = useState<any>(null);
  const items = (data?.items ?? []).filter((tx) => !q || (tx.display_name + tx.key + (tx.aliases ?? []).join(" ")).toLocaleLowerCase("tr-TR").includes(q.toLocaleLowerCase("tr-TR")));
  const save = async () => {
    if (!edit) return;
    setErr(null);
    try {
      const parsed = rules.trim() ? JSON.parse(rules) : null;
      const body: any = { unit_rules: parsed, canonical_unit: unit || null, info_what: infoText(infoWhat, raw(edit, "what")), info_low: infoText(infoLow, raw(edit, "low")), info_high: infoText(infoHigh, raw(edit, "high")) };
      if (!edit.is_builtin) Object.assign(body, { key: newKey.trim(), specimen });
      await api(`/api/app/catalog/tests/${edit.key}`, { method: "PATCH", body });
      setEdit(null);
      reload();
    } catch (e: any) {
      setErr(e instanceof SyntaxError ? { message: t("Kural JSON olarak okunamadı.") } : e);
    }
  };
  return (
    <div className="space-y-4">
      <input className="input max-w-sm" placeholder={t("Test, anahtar veya alias ara…")} value={q} onChange={(e) => setQ(e.target.value)} />
      <div className="card overflow-x-auto">
        <table className="table-clean w-full min-w-[900px]">
          <thead className="bg-surface2"><tr><th>{t("Test")}</th><th>{t("Anahtar")}</th><th>{t("Numune")}</th><th>{t("Kategori")}</th><th>{t("Birim")}</th><th>{t("Alias'lar")}</th><th></th></tr></thead>
          <tbody>
            {items.map((tx) => (
              <tr key={tx.key}>
                <td className="max-w-[260px]">
                  <div className="font-semibold">{tx.display_name}</div>
                  {tx.info_what ? (
                    <div className="mt-0.5 line-clamp-2 text-xs text-muted" title={tx.info_what}><Info size={11} className="mr-1 inline text-brand" />{tx.info_what}</div>
                  ) : (
                    <div className="mt-0.5 text-[11px] text-muted/70">{t("Açıklama yok")}</div>
                  )}
                </td>
                <td className="font-mono text-xs">{tx.key}</td>
                <td>{SPECIMEN_LABEL[tx.specimen]}</td>
                <td className="text-muted">{catLabel(tx.category)}</td>
                <td>{tx.canonical_unit ?? "—"}{tx.unit_rules && <div className="text-[11px] text-warn">{t("ölçek kuralı")}</div>}</td>
                <td className="max-w-[320px] text-xs text-muted">{(tx.aliases ?? []).join(", ")}</td>
                <td><button className="btn-ghost btn-sm" onClick={() => { setEdit(tx); setRules(tx.unit_rules ? JSON.stringify(tx.unit_rules) : ""); setUnit(tx.canonical_unit ?? ""); setNewKey(tx.key); setSpecimen(tx.specimen); setInfoWhat(raw(tx, "what") ?? ""); setInfoLow(raw(tx, "low") ?? ""); setInfoHigh(raw(tx, "high") ?? ""); }}><Pencil size={13} /></button></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <Modal open={!!edit} onClose={() => setEdit(null)} title={edit?.display_name ?? ""} wide
        footer={<><button className="btn-ghost" onClick={() => setEdit(null)}>{t("Vazgeç")}</button><button className="btn-primary" onClick={save}>{t("Kaydet ve yeniden hesapla")}</button></>}>
        <div className="space-y-3">
          {edit && !edit.is_builtin && (
            <div className="grid gap-3 sm:grid-cols-2">
              <Field label={t("Anahtar")} hint={t("numune.ad biçiminde, ör. blood.homosistein")}>
                <input className="input font-mono" value={newKey} onChange={(e) => setNewKey(e.target.value)} />
              </Field>
              <Field label={t("Numune")}>
                <select className="input" value={specimen} onChange={(e) => {
                  const v = e.target.value;
                  if (newKey.startsWith(`${specimen}.`)) setNewKey(`${v}.${newKey.slice(specimen.length + 1)}`);
                  setSpecimen(v);
                }}>
                  {["blood", "serum", "plasma", "urine", "other"].map((s) => <option key={s} value={s}>{SPECIMEN_LABEL[s]}</option>)}
                </select>
              </Field>
            </div>
          )}
          <div className="rounded-xl bg-surface2 px-3 py-2 text-xs text-muted">{t("Yerleşik test açıklamaları Türkçe saklanır ve diğer dillerde otomatik çevrilir. Değiştirdiğiniz metin tüm dillerde olduğu gibi gösterilir.")}</div>
          <Field label={t("Bu test nedir?")} hint={t("Herkesin anlayacağı sade bir dille yazın. Test detay sayfasında görünür.")}>
            <textarea className="input min-h-[90px] text-sm" value={infoWhat} onChange={(e) => setInfoWhat(e.target.value)} />
          </Field>
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label={edit ? infoLabels({ value_type: edit.value_type, info_low: infoLow }).low : t("Düşük çıkarsa")} hint={t("Anlamı yoksa boş bırakın.")}>
              <textarea className="input min-h-[110px] text-sm" value={infoLow} onChange={(e) => setInfoLow(e.target.value)} />
            </Field>
            <Field label={edit ? infoLabels({ value_type: edit.value_type, info_low: infoLow }).high : t("Yüksek çıkarsa")}>
              <textarea className="input min-h-[110px] text-sm" value={infoHigh} onChange={(e) => setInfoHigh(e.target.value)} />
            </Field>
          </div>
          <Field label={t("Standart birim")}><input className="input" value={unit} onChange={(e) => setUnit(e.target.value)} /></Field>
          <Field label={t("Ölçek kuralları (JSON)")} hint={t("Ör. dansite için: [{\"if_gt\": 100, \"factor\": 0.001}] — 1005 → 1.005. Değer ve referansa uygulanır; kayıtlı sonuçlar yeniden hesaplanır.")}>
            <textarea className="input font-mono text-xs" value={rules} onChange={(e) => setRules(e.target.value)} />
          </Field>
          <ErrorBox error={err} />
        </div>
      </Modal>
    </div>
  );
}

// ------------------------------------------------------------------ denetim kaydı

function AuditTab() {
  const [hide, setHide] = useState(true);
  const [page, setPage] = useState(0);
  const { data, loading } = useApi<any>(`/api/app/admin/audit?limit=50&offset=${page * 50}&hide_api_calls=${hide}`);
  return (
    <div className="space-y-3">
      <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={hide} onChange={(e) => { setHide(e.target.checked); setPage(0); }} /> {" "}{t("API/MCP çağrı kayıtlarını gizle")}</label>
      {loading && !data ? <Spinner /> : (
        <div className="card overflow-x-auto">
          <table className="table-clean w-full min-w-[860px]">
            <thead className="bg-surface2"><tr><th>{t("Zaman")}</th><th>{t("Aktör")}</th><th>{t("İşlem")}</th><th>{t("Kayıt")}</th><th>{t("Ayrıntı")}</th></tr></thead>
            <tbody>
              {data?.items.map((a: any) => (
                <tr key={a.id}>
                  <td className="whitespace-nowrap text-xs">{fmtDateTime(a.created_at)}</td>
                  <td className="text-sm">{a.actor_label} <span className="text-xs text-muted">({a.actor_type === "api_key" ? "anahtar" : a.actor_type === "user" ? t("kullanıcı") : "sistem"})</span></td>
                  <td><code className="text-xs">{a.action}</code></td>
                  <td className="font-mono text-xs text-muted">{a.entity} {a.entity_id}</td>
                  <td className="max-w-[360px] truncate font-mono text-[11px] text-muted" title={JSON.stringify(a.payload_diff)}>{a.payload_diff ? JSON.stringify(a.payload_diff) : ""}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <div className="flex items-center gap-2 text-sm">
        <button className="btn-ghost btn-sm" disabled={page === 0} onClick={() => setPage(page - 1)}>{t("Önceki")}</button>
        <span className="text-muted">{page * 50 + 1}–{Math.min((page + 1) * 50, data?.total ?? 0)} / {data?.total ?? 0}</span>
        <button className="btn-ghost btn-sm" disabled={(page + 1) * 50 >= (data?.total ?? 0)} onClick={() => setPage(page + 1)}>{t("Sonraki")}</button>
      </div>
    </div>
  );
}

// ------------------------------------------------------------------ yedekleme

function BackupTab() {
  const { data, reload } = useApi<any>("/api/app/admin/backups");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<any>(null);
  const run = async () => {
    setBusy(true);
    setErr(null);
    try {
      await api("/api/app/admin/backups", { method: "POST" });
      reload();
    } catch (e) {
      setErr(e);
    } finally {
      setBusy(false);
    }
  };
  const size = (b: number) => (b > 1e6 ? `${(b / 1e6).toFixed(1)} MB` : `${Math.ceil(b / 1e3)} KB`);
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <p className="max-w-2xl text-sm text-muted">{t("Veritabanı, PDF'ler ve avatarlar her gün otomatik olarak şifrelenip")}{" "}<code>data/backups</code> {" "}{t("klasörüne yedeklenir ve 30 gün saklanır. Şifre çözme anahtarı")}{" "}<code>.env</code> {" "}{t("içindeki")}{" "}<code>DATA_ENCRYPTION_KEY</code>{t("'dir.")}</p>
        <button className="btn-primary ml-auto" onClick={run} disabled={busy}><Database size={16} /> {busy ? t("Yedekleniyor…") : t("Şimdi yedekle")}</button>
      </div>
      <ErrorBox error={err} />
      {data?.status?.last_error && <ErrorBox error={{ message: t("Son yedekleme hatası: ") + data.status.last_error }} />}
      {!data?.items?.length ? <Empty title={t("Henüz yedek yok")} /> : (
        <div className="card overflow-x-auto">
          <table className="table-clean w-full">
            <thead className="bg-surface2"><tr><th>{t("Dosya")}</th><th>{t("Tarih")}</th><th>{t("Boyut")}</th><th></th></tr></thead>
            <tbody>
              {data.items.map((b: any) => (
                <tr key={b.name}><td className="font-mono text-xs">{b.name}</td><td>{fmtDateTime(b.created_at)}</td><td>{size(b.size)}</td>
                  <td><a className="btn-ghost btn-sm" href={`/api/app/admin/backups/${b.name}`}><Download size={13} /> {" "}{t("İndir")}</a></td></tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <div className="card p-4 text-sm">
        <div className="mb-1 font-bold">{t("Geri yükleme")}</div>
        <pre className="overflow-x-auto rounded-xl bg-surface2 p-3 text-xs">docker compose exec app rimetra restore /data/backups/&lt;dosya&gt;.tar.enc{"\n"}docker compose restart app</pre>
      </div>
    </div>
  );
}

export default function Admin() {
  const [sp, setSp] = useSearchParams();
  const tab = sp.get("sekme") ?? "uyeler";
  return (
    <div className="space-y-5">
      <h1 className="text-[36px] font-extrabold tracking-tight">{t("Yönetim")}</h1>
      <div className="flex gap-1 overflow-x-auto rounded-2xl border border-line bg-surface p-1">
        {TABS.map((tx) => (
          <button key={tx.id} onClick={() => setSp({ sekme: tx.id }, { replace: true })}
            className={`flex shrink-0 items-center gap-2 rounded-xl px-4 py-2 text-sm font-semibold ${tab === tx.id ? "bg-brand text-white dark:text-[#10201a]" : "text-muted hover:bg-surface2 hover:text-ink"}`}>
            <tx.icon size={16} /> {tx.label}
          </button>
        ))}
      </div>
      {tab === "uyeler" && <MembersTab />}
      {tab === "anahtarlar" && <KeysTab />}
      {tab === "baglanti" && <ConnectTab />}
      {tab === "telegram" && <TelegramTab />}
      {tab === "katalog" && <CatalogTab />}
      {tab === "denetim" && <AuditTab />}
      {tab === "yedek" && <BackupTab />}
    </div>
  );
}
